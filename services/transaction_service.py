# services/transaction_service.py
import datetime
import os
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
import logging

from tronpy import Tron
from tronpy.keys import PrivateKey, to_base58check_address

from crud.transaction import get_transaction_by_id,get_transactions_by_tx_id,update_reward_trade_hash
from queen.task_queue import tx_task_queue
from queen.model import TxTask
from decimal import Decimal, ROUND_DOWN
from fastapi.responses import JSONResponse
from fastapi import status

PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
NETWORK = os.getenv("NETWORK")
USDT_CONTRACT_ADDRESS = os.getenv("USDT_CONTRACT_ADDRESS")

client = Tron(network=NETWORK)
FEE_RESERVE_SUN = 100_000  # 预留手续费，约 0.1 TRX；按需调整
SUN_PER_TRX = 1_000_000

def get_by_id(tx_id: int, db: Session):
    tx = get_transaction_by_id(db,tx_id)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="交易不存在")
    return tx

def transfer(tx_id: int, db: Session):
    try:
        # 读取订单
        transaction = get_by_id(db=db, tx_id=tx_id)
        if transaction is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "订单不存在"}
            )

        # 幂等/唯一性检查
        records = get_transactions_by_tx_id(db=db, tx_id=transaction.transaction_id)
        if records and len(records) > 1:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "存在相同订单号的订单"}
            )

        # 已处理过
        if transaction.reward_trade_hash:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "当前订单已处理过"}
            )

        # 业务前置校验
        if not transaction.is_win:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "当前下注结果不是赢"}
            )

        # 金额校验
        reward_dec = Decimal(str(transaction.reward or "0"))
        if reward_dec <= 0:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "返利小于等于 0"}
            )

        # ===== 金额放大到最小单位（整数）=====
        # 例如 USDT/TRX 在 Tron 上通常是 6 位小数
        token_decimals = int(transaction.token_decimal or 0)
        scale = Decimal(10) ** token_decimals
        # 使用量化避免浮点误差；向下取整以避免超发
        amount_int = int((reward_dec * scale).quantize(Decimal("1"), rounding=ROUND_DOWN))
        if amount_int <= 0:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "放大后金额为 0"}
            )

        # ===== 选择币种并发起转账（异常→failed）=====
        to_addr = transaction.from_

        try:
            if transaction.token_symbol == "USDT":
                reward_tx_id = transfer_usdt(
                    to_address=to_addr,
                    usdt_amount=amount_int,  # USDT 的最小单位
                )
            elif transaction.token_symbol == "TRX":
                reward_tx_id = transfer_trx(
                    to_address=to_addr,
                    amount=amount_int,         # TRX 最小单位 sun
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"detail": f"暂不支持的代币：{transaction.token_symbol}"}
                )
        except ValueError as e:
            logging.warning("奖励转账失败（余额不足）：%s", e)
            update_reward_trade_hash(db=db, tx_id=tx_id, hash_value="",status=2)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": "failed", "detail": str(e)}
            )
        except Exception as e:
            # 任何链上异常都视为 failed
            logging.exception("链上转账失败：tx_id=%s, token=%s, to=%s, amount=%s",
                              tx_id, transaction.token_symbol, to_addr, amount_int)
            db.rollback()  # 防止前面有人开启了事务
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": "failed", "detail": str(e)}
            )

        # ===== 只有成功才落库并入队 =====
        update_reward_trade_hash(db=db, tx_id=transaction.id, hash_value=reward_tx_id,status=1)
        try:
            db.commit()
        except Exception:
            logging.exception("更新 reward_trade_hash 提交失败，准备回滚并返回 failed")
            db.rollback()
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": "failed", "detail": "数据库提交失败"}
            )

        # 入队异步查询任务（用链上 txid & 业务订单 id）
        try:
            task = TxTask(
                tx_id=reward_tx_id,      # 链上交易哈希
                db_session=db,
                transaction_id=transaction.id,
                delay=60,
                client=client,
                payload_builder=build_transfer_payload
            )
            tx_task_queue.put(task)
        except Exception:
            # 入队失败不回滚已提交的链上交易和DB更新；仅记录日志
            logging.exception("入队异步查询任务失败（不影响链上已成功的转账）")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok", "txid": reward_tx_id}
        )

    except JSONResponse as r:  # 若上面直接返回 JSONResponse
        return r
    except Exception as e:
        # 兜底异常 → failed
        logging.exception("处理 transfer(%s) 发生未预期异常：%s", tx_id, e)
        try:
            db.rollback()
        except Exception:
            pass
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "failed", "detail": "服务器内部错误"}
        )


def hex_to_base58(addr_hex: str) -> str:
    from tronpy.keys import to_base58check_address
    return to_base58check_address(bytes.fromhex(addr_hex))


def transfer_trx(to_address, amount):
    priv_key = PrivateKey(bytes.fromhex(PRIVATE_KEY))
    from_addr = priv_key.public_key.to_base58check_address()
    # 1) 余额检查（含手续费缓冲）
    balance_sun = get_balance_sun(client, from_addr)
    need_sun = amount + FEE_RESERVE_SUN
    if balance_sun < need_sun:
        shortage = need_sun - balance_sun
        msg = (
            f"余额不足：需 {need_sun} sun（含手续费缓冲 {FEE_RESERVE_SUN}），"
            f"当前仅 {balance_sun} sun，差 {shortage} sun。"
        )
        logging.error(msg)
        raise ValueError(msg)
    logging.info(f"🚀 开始原生转账 TRX: {amount} 到 {to_address}）")

    # 2) 构建-签名-广播
    try:
        txn = (
            client.trx.transfer(
                from_addr,     # from
                to_address,    # to
                amount     # 金额（sun）
            )
            .build()
            .sign(priv_key)
            .broadcast()
        )
    except Exception as e:
        # 网络/RPC 异常
        logging.exception("广播失败：%s", e)
        raise

    # 3) 节点返回校验
    # tronpy 常见返回：{'result': True/False, 'txid': '...'} 或带 'code'/'message'
    if isinstance(txn, dict):
        if txn.get("result") is True and "txid" in txn:
            txid = txn["txid"]
            logging.info(f"✅ 已发送 TRX 原生转账，TxID: {txid}")
            return txid
        # 处理常见错误形态
        err_code = txn.get("code") or txn.get("Error")
        err_msg = txn.get("message") or txn.get("Message") or "未知错误"
        detail = f"code={err_code}, message={err_msg}, raw={txn}"
        logging.error("广播返回失败：%s", detail)
        raise RuntimeError(f"广播失败：{detail}")

    # 非预期返回
    logging.error("未知的返回格式：%r", txn)
    raise RuntimeError(f"未知的返回格式：{txn!r}")

def transfer_usdt( to_address, usdt_amount: int):
    """
    转账 USDT（TRC20）到指定地址


    :param to_address: 接收方钱包地址（T开头）
    :param usdt_amount: USDT 金额（float，如 20.5）
    """
    logging.info(f"🚀 开始转账 USDT {usdt_amount} 到 {to_address}")
    # 初始化客户端和私钥
    client = Tron(network=NETWORK)
    private_key = PrivateKey(bytes.fromhex(PRIVATE_KEY))
    owner_address = private_key.public_key.to_base58check_address()
    # 加载 USDT 合约
    contract = client.get_contract(USDT_CONTRACT_ADDRESS)
    logging.info(f"🎯 接收地址: {to_address}")
    amount_sun = usdt_amount
    logging.info(f"🔎 USDT 余额: {contract.functions.balanceOf(owner_address)}")
    logging.info(f"📦 要转金额: {usdt_amount}")
    assert usdt_amount <= contract.functions.balanceOf(owner_address), "余额不足"
    # 构造交易
    txn = (
        contract.functions.transfer(to_address, amount_sun)
        .with_owner(owner_address)
        .fee_limit(10_000_000)
        .build()
        .sign(private_key)
        .broadcast()
    )

    logging.info(f"✅ 已发送 USDT 交易，TxID: {txn['txid']}")
    return txn['txid']


def build_transfer_payload(tx_info):
    receipt = tx_info.get("receipt", {})
    timestamp_ms = tx_info.get("blockTimeStamp", 0)

    if timestamp_ms > 0:
        timestamp_s = int(timestamp_ms / 1000)
        dt = datetime.datetime.fromtimestamp(timestamp_s, tz=datetime.timezone.utc)
    # 转成 naive UTC datetime（去掉 tzinfo，否则某些驱动也会报错）
        block_time_dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    else:
        block_time_dt = None

    payload = {
        "tradeID": tx_info.get("id", ""),
        "fee": tx_info.get("fee", 0),
        "blockNumber": tx_info.get("blockNumber", 0),
        "blockTimeStamp": block_time_dt,  # ✅ 含时区
        "contractResult": tx_info.get("contractResult", [""])[0],
        "contractAddress": tx_info.get("contract_address", ""),
        "receiptOriginEnergyUsage": receipt.get("origin_energy_usage", 0),
        "receiptEnergyUsageTotal": receipt.get("energy_usage_total", 0),
        "receiptNetFee": receipt.get("net_fee", 0),
        "receiptResult": receipt.get("result", "")
    }

    return payload

def parse_iso_to_mysql_dt(iso_str: str) -> datetime:
    # 兼容 "2025-08-18T12:11:51+00:00" 这类字符串
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    # 统一转 UTC，然后去掉 tzinfo（naive）
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def get_balance_sun(client, address_base58: str) -> int:
    """
    返回账户余额（sun）
    """
    # tronpy 的 get_account_balance 通常返回 TRX；乘回 sun
    bal_trx = client.get_account_balance(address_base58)
    return int(bal_trx * SUN_PER_TRX)