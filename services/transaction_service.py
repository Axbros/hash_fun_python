# services/transaction_service.py
import datetime
import os

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status
import logging

from tronpy import Tron
from tronpy.keys import PrivateKey, to_base58check_address

from crud.transaction import get_transaction_by_id,get_transactions_by_tx_id,update_reward_trade_hash
from queen.task_queue import tx_task_queue
from queen.model import TxTask
from decimal import Decimal
from fastapi.responses import JSONResponse
from fastapi import status

PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
NETWORK = os.getenv("NETWORK")
USDT_CONTRACT_ADDRESS = os.getenv("USDT_CONTRACT_ADDRESS")

client = Tron(network=NETWORK)

def get_by_id(tx_id: int, db: Session):
    tx = get_transaction_by_id(db,tx_id)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="交易不存在")
    return tx

def transfer(tx_id:int,db:Session):
    transaction = get_by_id(db=db,tx_id=tx_id)
    records=get_transactions_by_tx_id(db=db,tx_id=transaction.transaction_id)
    reward_tx_id = ""
    if len(records) > 1:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "存在相同订单号的订单"}
        )
    if transaction.reward_trade_hash != "":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "当前订单已处理过"}
        )
    if not transaction.is_win:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "当前下注结果不是赢"}
        )
    if transaction.reward <= 0:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "返利小于0"}
        )

    # 正确：先把 float 转为 string 再用 Decimal 保证精度
    amount_str = str(transaction.reward)  # 或者让 reward 本身就是字符串
    scale = Decimal(10) ** transaction.token_decimal
    amount = int(Decimal(amount_str) * scale)
    if transaction.token_symbol == "USDT":
        reward_tx_id=transfer_usdt(transaction.from_,amount)
    if transaction.token_symbol =="TRX":
        reward_tx_id=transfer_trx(transaction.from_,amount)
    update_reward_trade_hash(db=db,tx_id=transaction.id,hash_value=reward_tx_id)

    # 延时队列查询订单状态
    task = TxTask(
        tx_id=reward_tx_id,
        db_session=db,
        transaction_id=tx_id,
        delay=60,
        client=client,
        payload_builder=build_transfer_payload
    )
    tx_task_queue.put(task)
    return "ok"


def hex_to_base58(addr_hex: str) -> str:
    from tronpy.keys import to_base58check_address
    return to_base58check_address(bytes.fromhex(addr_hex))


def transfer_trx(to_address, amount):

    """
   原生 TRX 转账函数（单位：sun）

   :param to_address: 接收方地址（Base58 格式，如 TX...）
   :param amount: 转账金额，单位是 sun（1 TRX = 1_000_000 sun）
   :return: 交易 ID
   """
    priv_key = PrivateKey(bytes.fromhex(PRIVATE_KEY))  # ✅ hex 私钥

    logging.info(f"🚀 开始原生转账 TRX: {amount} 到 {to_address}）")

    txn = (
        client.trx.transfer(
            priv_key.public_key.to_base58check_address(),  # from
            to_address,                                    # to
            amount                                          # 单位：sun
        )
        .build()
        .sign(priv_key)
        .broadcast()
    )

    logging.info(f"✅ 已发送 TRX 原生转账，TxID: {txn['txid']}")
    return txn['txid']

def transfer_usdt( to_address: str, usdt_amount: int):
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
        dt = datetime.datetime.fromtimestamp(timestamp_s, tz=datetime.timezone.utc)  # 指定 UTC
        block_time_str = dt.isoformat()  # e.g., '2025-07-31T08:53:21+00:00'
    else:
        block_time_str = None

    payload = {
        "tradeID": tx_info.get("id", ""),
        "fee": tx_info.get("fee", 0),
        "blockNumber": tx_info.get("blockNumber", 0),
        "blockTimeStamp": block_time_str,  # ✅ 含时区
        "contractResult": tx_info.get("contractResult", [""])[0],
        "contractAddress": tx_info.get("contract_address", ""),
        "receiptOriginEnergyUsage": receipt.get("origin_energy_usage", 0),
        "receiptEnergyUsageTotal": receipt.get("energy_usage_total", 0),
        "receiptNetFee": receipt.get("net_fee", 0),
        "receiptResult": receipt.get("result", "")
    }

    return payload

