class TxTask:
    def __init__(
            self,
            tx_id: str,
            db_session,
            transaction_id: int,
            delay: int = 10,
            client=None,
            payload_builder=None
    ):
        self.tx_id = tx_id
        self.db_session = db_session
        self.transaction_id = transaction_id
        self.delay = delay
        self.client = client
        self.payload_builder = payload_builder
