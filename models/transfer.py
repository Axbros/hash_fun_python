from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Transfer(Base):
    __tablename__ = "transfer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transaction.id"), unique=True, nullable=False)
    trade_id = Column(String(100), comment="交易哈希 ID")
    fee = Column(Integer, comment="手续费（Sun）")
    block_number = Column(Integer)
    block_timeStamp = Column(DateTime)
    contract_result = Column(String(100))
    contract_address = Column(String(100))
    receipt_origin_energy_usage = Column(Integer)
    receipt_energy_usage_total = Column(Integer)
    receipt_net_fee = Column(Integer)
    receipt_result = Column(String(50))
    reason = Column(String(50))
    updated_at = Column(DateTime)
    created_at = Column(DateTime)
    deleted_at = Column(DateTime)
