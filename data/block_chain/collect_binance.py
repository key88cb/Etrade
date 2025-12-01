import argparse
import io
import math
import sys
import time
import traceback
from typing import Optional

import pandas as pd
import psycopg2
import yaml
from loguru import logger

from .task import check_task, update_task_status

# 默认配置
with open("./config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

db_config = config.get("db", {})
csv_path = "./ETHUSDT-trades-2025-09.csv"
COLUMN_NAMES = ["id", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"]
DTYPE_MAP = {
    "id": "int64",
    "price": "float64",
    "qty": "float64",
    "quoteQty": "float64",
    "time": "int64",
    "isBuyerMaker": "bool",
    "isBestMatch": "bool",
}


def count_lines(task_id: str, filepath: str) -> Optional[int]:
    """
    描述：估算文件总行数，用于百分比导入控制
    参数：filepath: 文件路径
    返回值：文件总行数
    """
    try:
        logger.info(f"正在估算文件总行数: {filepath}")
        start_time = time.time()
        count = 0
        with open(filepath, "r", encoding="utf-8") as file:
            for _ in file:
                count += 1
                if count % 1000000 == 0:
                    logger.info(f"已估算 {count} 行数据")
                    if check_task(task_id):
                        logger.info(f"任务 {task_id} 已取消，停止估算 Binance 数据")
                        break
        end_time = time.time()
        logger.info(
            f"估算完成，共约 {count} 行数据，耗时 {end_time - start_time:.2f} 秒。"
        )
        return count
    except FileNotFoundError:
        logger.error(f"找不到CSV文件 '{filepath}'。请检查路径是否正确。")
        update_task_status(task_id, "TASK_STATUS_FAILED")
        raise
    except Exception as e:
        logger.warning(f"估算行数失败: {e}. 无法按百分比导入。")
        update_task_status(task_id, "TASK_STATUS_FAILED")
        raise

def process_chunk(
    task_id: str,
    chunk_data: pd.DataFrame,
    chunk_index: int,
    rows_counter,
    target_rows: Optional[int],
):
    """
    描述：处理单个分块：预处理数据并写入数据库
    参数：task_id: 任务ID, chunk_data: 分块数据, chunk_index: 分块索引, rows_counter: 计数器, target_rows: 目标行数
    返回值：成功标志, 处理行数, 导入行数, 是否停止标志
    """
    original_chunk_len = len(chunk_data)
    chunk = chunk_data.copy()
    chunk.rename(
        columns={
            "time": "trade_time",
            "quoteQty": "quote_qty",
            "isBuyerMaker": "is_buyer_maker",
            "isBestMatch": "is_best_match",
        },
        inplace=True,
    )
    chunk["trade_time"] = pd.to_datetime(
        chunk["trade_time"], unit="us", utc=True, errors="coerce"
    )
    chunk.dropna(subset=["trade_time"], inplace=True)
    if chunk.empty:
        rows_counter[0] += original_chunk_len
        should_stop = target_rows is not None and rows_counter[0] >= target_rows
        return True, original_chunk_len, 0, should_stop
    try:
        csv_buffer = io.StringIO()
        chunk.to_csv(csv_buffer, index=False, header=False)
        csv_buffer.seek(0)
        columns = "id, price, qty, quote_qty, trade_time, is_buyer_maker, is_best_match"
        copy_sql = f"COPY binance_trades ({columns}) FROM STDIN WITH (FORMAT CSV)"
        with psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            dbname=db_config["database"],
            user=db_config["username"],
            password=db_config["password"],
        ) as conn:
            with conn.cursor() as cursor:
                cursor.copy_expert(sql=copy_sql, file=csv_buffer)
            conn.commit()
        rows_imported = len(chunk)
        rows_counter[0] += original_chunk_len
        rows_counter[1] += rows_imported
        should_stop = target_rows is not None and rows_counter[0] >= target_rows
        return True, original_chunk_len, rows_imported, should_stop
    except Exception as e:
        logger.error(f"处理分块时发生意外错误: {e}")
        update_task_status(task_id, "TASK_STATUS_FAILED")
        raise

def import_data_to_database(task_id: str, target_rows: Optional[int], total_lines: Optional[int], chunk_size: int):
    """
    描述：主导入逻辑：读取CSV，分块处理并写入数据库。
    参数：target_rows: 目标行数, total_lines: 总行数, chunk_size: 分块大小
    返回值：处理行数, 导入行数
    """
    rows_counter = [0, 0]
    try:
        logger.info("正在读取CSV文件分块并导入...")
        chunk_iterator = pd.read_csv(
            csv_path,
            chunksize=chunk_size,
            header=None,
            names=COLUMN_NAMES,
            usecols=COLUMN_NAMES,
            dtype=DTYPE_MAP,
            engine="c",
            low_memory=False,
            memory_map=True,
            on_bad_lines="skip",
        )
        should_stop = False
        for i, chunk in enumerate(chunk_iterator):
            if check_task(task_id):
                logger.info(f"任务 {task_id} 已取消，停止导入 Binance 数据")
                break
            _, _, _, stop_flag = process_chunk(
                task_id,
                chunk,
                i,
                rows_counter,
                target_rows,
            )
            if stop_flag and not should_stop:
                logger.info(
                    f"已处理约 {rows_counter[0]} 行，达到目标 {target_rows} 行。"
                )
                should_stop = True
                break
    except FileNotFoundError:
        logger.error(f"找不到CSV文件 '{csv_path}'。请检查路径是否正确。")
        update_task_status(task_id, "TASK_STATUS_FAILED")
        raise
    except Exception as e:
        logger.error(f"处理文件时发生意外错误: {e}")
        traceback.print_exc(file=sys.stderr)
        update_task_status(task_id, "TASK_STATUS_FAILED")
        raise
    return rows_counter


def _calc_target_rows(
    total_lines: Optional[int], import_percentage: int
) -> Optional[int]:
    if total_lines is None:
        return None
    if import_percentage >= 100:
        return total_lines
    return math.ceil(total_lines * (import_percentage / 100))

def collect_binance(
    task_id: str, csv_path: str, import_percentage: int, chunk_size: int
):
    try:
        start_time = time.time()
        total_lines = count_lines(task_id, csv_path)
        if check_task(task_id):
            logger.info(f"任务 {task_id} 已取消，停止导入 Binance 数据")
            return 0
        target_rows = _calc_target_rows(total_lines, import_percentage)
        rows_counter = import_data_to_database(task_id, target_rows, total_lines, chunk_size)
        total_time = time.time() - start_time
        if check_task(task_id):
            logger.info(f"任务 {task_id} 已取消，停止导入 Binance 数据")
            return 0
        logger.info(f"成功导入 {rows_counter[1]} 行，耗时 {total_time:.2f}s")
        update_task_status(task_id, "TASK_STATUS_SUCCESS")
        return rows_counter[1]
    except Exception as e:
        logger.error(f"导入 Binance 数据失败: {e}")
        update_task_status(task_id, "TASK_STATUS_FAILED")
        raise

if __name__ == "__main__":
    collect_binance("1", csv_path, 1, 1000000)