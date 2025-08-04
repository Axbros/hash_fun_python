from sqlalchemy.orm import Session
from models.transfer import Transfer
import datetime

def insert_transfer_record(db: Session, payload: dict, transaction_id: int):
    # 生成 Transfer 实例
    transfer = Transfer(
        transaction_id=transaction_id,
        trade_id=payload.get("tradeID", ""),
        fee=payload.get("fee", 0),
        block_number=payload.get("blockNumber", 0),
        block_timeStamp=payload.get("blockTimeStamp"),  # 已是 datetime 类型或 None
        contract_result=payload.get("contractResult", ""),
        contract_address=payload.get("contractAddress", ""),
        receipt_origin_energy_usage=payload.get("receiptOriginEnergyUsage", 0),
        receipt_energy_usage_total=payload.get("receiptEnergyUsageTotal", 0),
        receipt_net_fee=payload.get("receiptNetFee", 0),
        receipt_result=payload.get("receiptResult", ""),
        created_at=datetime.datetime.utcnow()
    )

    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return transfer
