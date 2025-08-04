# services/transaction_service.py
import os

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status
import logging

from tronpy import Tron
from tronpy.keys import PrivateKey

from crud.transaction import get_transaction_by_id,get_transactions_by_tx_id,update_reward_trade_hash

PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
NETWORK = os.getenv("NETWORK")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

def get_by_id(tx_id: int, db: Session):
    tx = get_transaction_by_id(db,tx_id)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="交易不存在")
    return tx

def transfer(tx_id:int,db:Session):
    transaction = get_by_id(db=db,tx_id=tx_id)
    records=get_transactions_by_tx_id(db=db,tx_id=transaction.transaction_id)
    reward_tx_id = ""
    if len(records)>1:
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="存在相同订单号的订单")
    if transaction.reward_trade_hash != "":
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="当前订单已处理过")
    if not transaction.is_win:
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="当前下注结果不是赢")
    if transaction.reward <=0:
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="返利小于0")
    if transaction.token_symbol == "USDT":
        reward_tx_id=transfer_usdt(transaction.from_,int(transaction.reward*10**transaction.token_decimal))
    if transaction.token_symbol =="TRX":
        reward_tx_id=transfer_trx(transaction.from_,int(transaction.reward*10**transaction.token_decimal))
    update_reward_trade_hash(db=db,tx_id=transaction.id,hash_value=reward_tx_id)
    return transaction





def transfer_trx(to_address, amount):
    logging.info(f"🚀 开始转账 TRX {amount} 到 {to_address}")
    client = Tron(network=NETWORK)
    contract = client.get_contract(CONTRACT_ADDRESS)
    private_key = PrivateKey(bytes.fromhex(PRIVATE_KEY))  # 非 base58，要 hex
    txn = (
        contract.functions.transfer(to_address, amount)
        .with_owner(private_key.public_key.to_base58check_address())  # 非 base58，要 hex
        .fee_limit(5_000_000)
        .build()
        .sign(private_key)
        .broadcast()
    )
    logging.info(f"🚀 已发送 TRX 交易，TxID: {txn['txid']}")
    logging.info("================================================")
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
    contract = client.get_contract(CONTRACT_ADDRESS)
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


