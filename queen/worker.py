from queue import Queue
import time
import logging
from crud.transfer import insert_transfer_record

def transaction_worker(task_queue: Queue):
    while True:
        task = task_queue.get()
        if not task:
            continue

        logging.info(f"⏳ 等待 {task.delay}s 后查询交易：{task.tx_id}")
        time.sleep(task.delay)

        try:
            tx_info = task.client.get_transaction_info(task.tx_id)
            payload = task.payload_builder(tx_info)

            result = tx_info.get("receipt", {}).get("result")
            logging.info(f"🔍 链上状态 result={result}")

            if result != "SUCCESS":
                logging.info(result)
                logging.warning(f"⚠️ 链上交易失败：{task.tx_id}")
            else:
                logging.info(f"✅ 链上交易成功，写入数据库")
            insert_transfer_record(task.db_session, payload, task.transaction_id)
        except Exception as e:
            logging.error(f"🔥 异常：{e}")

        task_queue.task_done()
