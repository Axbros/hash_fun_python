class TxTask:
    def __init__(
            self,
            tx_id: str,
            transaction_id: int,
            delay: int = 10,
            client=None,
            payload_builder=None
    ):
        self.tx_id = tx_id
        self.transaction_id = transaction_id
        self.delay = delay
        self.client = client
        self.payload_builder = payload_builder
