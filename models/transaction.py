from pydantic import BaseModel

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Transaction:
    id: int
    transactionID: str
    tokenSymbol: str
    tokenAddress: Optional[str]
    tokenDecimal: int
    tokenName: str
    blockNumber: int
    blockHash: str
    blockDx: Optional[str]
    blockDs: Optional[str]
    blockTimestamp: datetime
    from_: str
    to: str
    type: str
    value: str
    isWin: int   # ✅ 改回驼峰，和 API 一致
    odds: float
    reward: float
    reward_trade_hash: str
    createdAt: datetime
    updatedAt: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(
            id=data["id"],
            transactionID=data["transactionID"],
            tokenSymbol=data["tokenSymbol"],
            tokenAddress=data.get("tokenAddress"),
            tokenDecimal=int(data["tokenDecimal"]),
            tokenName=data["tokenName"],
            blockNumber=int(data["blockNumber"]),
            blockHash=data["blockHash"],
            blockDx=data.get("blockDx"),
            blockDs=data.get("blockDs"),
            blockTimestamp=datetime.fromisoformat(data["blockTimestamp"]),
            from_=data["from"],
            to=data["to"],
            type=data["type"],
            value=data["value"],
            isWin=int(data["isWin"]),   # ✅ 直接对上
            odds=float(data["odds"]),
            reward=float(data["reward"]),
            reward_trade_hash=data.get("reward_trade_hash", ""),
            createdAt=datetime.fromisoformat(data["createdAt"]),
            updatedAt=datetime.fromisoformat(data["updatedAt"]),
        )


class TransactionResponse(BaseModel):
    code: int
    msg: str
    data: dict  # 你也可以直接放 Transaction，但这里保留灵活性
