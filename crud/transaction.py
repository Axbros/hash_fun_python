# crud/transaction.py
from typing import Type

from sqlalchemy.orm import Session
from models.transaction import Transaction

def get_transaction_by_id(db: Session, id: int) -> Type[Transaction] | None:
    return db.query(Transaction).filter(Transaction.id == id).first()

def get_transactions_by_tx_id(db: Session, tx_id: str) -> list[Type[Transaction]]:
    return db.query(Transaction).filter(Transaction.transaction_id == tx_id).all()

def update_reward_trade_hash(db: Session, tx_id: int, hash_value: str) -> Transaction:
    tx = db.query(Transaction).get(tx_id)
    if not tx:
        raise ValueError("交易记录不存在")

    tx.reward_trade_hash = hash_value
    db.commit()
    db.refresh(tx)
    return tx