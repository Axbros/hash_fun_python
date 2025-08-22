# crud/transaction.py
from typing import Type

import requests

from crud import GO_HTTP_URL
from models.transaction import Transaction, TransactionResponse


def get_transaction_by_id(transaction_id: str) -> Type[TransactionResponse] | None:
    url=GO_HTTP_URL+"/transaction/"+transaction_id
    return requests.get(url).json()



def get_transactions_by_tx_id(tx_id: str) -> Type[TransactionResponse]:
    url=GO_HTTP_URL+"/transaction/list"
    body={
        "page":1,
        "size":10,
        "limit":10,
        "sort":"transaction_id",
        "columns":[
            {
                "name":"transaction_id",
                "value":tx_id,
            }
        ]
    }
    return requests.post(url,json=body).json()

def update_reward_trade_hash(tx_id: str, hash_value: str,status:int) -> Transaction:
    url=GO_HTTP_URL+"/transaction/"+tx_id
    body={
        "reward_trade_hash":hash_value,
        "status":status
    }
    return requests.put(url,json=body).json()
