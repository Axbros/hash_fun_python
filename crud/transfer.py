import requests

from crud import GO_HTTP_URL


def insert_transfer_record(payload: dict, transaction_id: int):
    url = GO_HTTP_URL+"/transfer/"
    body={
        "transaction_id":transaction_id,
        "tradeID":payload.get("tradeID", ""),
        "fee":payload.get("fee", 0),
        "blockNumber":payload.get("blockNumber", 0),
        "blockTimeStamp":payload.get("blockTimeStamp"),  # 已是 datetime 类型或 None
        "contractResult":payload.get("contractResult", ""),
        "contractAddress":payload.get("contractAddress", ""),
        "receiptOriginEnergyUsage":payload.get("receiptOriginEnergyUsage", 0),
        "receiptEnergyUsageTotal":payload.get("receiptEnergyUsageTotal", 0),
        "receiptNetFee":payload.get("receiptNetFee", 0),
        "receiptResult":payload.get("receiptResult", ""),
    }
    return requests.post(url,json=body).json()
