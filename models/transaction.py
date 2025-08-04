from sqlalchemy import Column, Integer, String, DateTime, Float

from database import Base


class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(128), unique=True, comment="交易ID/交易哈希")
    token_symbol = Column(String(32), comment="代币符号如USDT")
    token_address = Column(String(64), comment="合约地址")
    token_decimal = Column(Integer, comment="精度")
    token_name = Column(String(32), comment="完整名称")
    block_number = Column(Integer, comment="区块编号")
    block_hash = Column(String(64), comment="区块哈希")
    game_type = Column(String(32))
    result_number = Column(Integer, comment="区块结果")
    is_result_ge5 = Column(Integer)
    is_result_even = Column(Integer)
    block_timestamp = Column(DateTime, comment="上链时间")
    from_ = Column("from", String(64), comment="发送方地址")
    to = Column(String(64), comment="接收方地址")
    type = Column(String(32), comment="交易类型")
    value = Column(String(32), comment="原始数量")
    calculated_value = Column(Integer, comment="真实整数金额")
    actual_amount = Column(Float, comment="真实金额")
    is_win = Column(Integer)
    odds = Column(Float, comment="赔率")
    reward = Column(Float)
    reward_trade_hash = Column(String(64), comment="回款交易哈希")
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    deleted_at = Column(DateTime)
