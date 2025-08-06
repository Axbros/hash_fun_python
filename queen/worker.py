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
            logging.info(f"tx_info={tx_info}")
            payload = task.payload_builder(tx_info)

            result = tx_info.get("receipt", {}).get("result")
            if result is None:
                # 没有 result 字段 → 非合约调用，比如 TRX 转账
                logging.info("ℹ️ 非合约交易（无 result 字段），假设已成功")
            else:
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
