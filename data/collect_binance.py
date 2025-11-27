import argparse
import io
import math
import sys
import time
import traceback
from typing import Any, Optional

import pandas as pd
import psycopg2
import yaml
from loguru import logger
from tqdm import tqdm

from task_client import TaskClient, load_config_from_string

# 默认配置
with open("config/config.yaml", "r", encoding="utf-8") as file:
    _CONFIG = yaml.safe_load(file)

DEFAULT_DB_CONFIG = _CONFIG.get("db", {})
DEFAULT_CSV_FILE_PATH = "./ETHUSDT-trades-2025-09.csv"
DEFAULT_IMPORT_PERCENTAGE = 1
DEFAULT_CHUNK_SIZE = 1_000_000
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


def count_lines(filepath: str) -> Optional[int]:
    """
    描述：估算文件总行数，用于百分比导入控制
    参数：filepath: 文件路径
    返回值：文件总行数
    """
    try:
        logger.info("正在估算文件总行数: %s", filepath)
        start_time = time.time()
        count = sum(1 for _ in open(filepath, "rb"))
        end_time = time.time()
        logger.info("估算完成，共约 %s 行数据，耗时 %.2f 秒。", count, end_time-start_time)
        return count
    except FileNotFoundError:
        logger.error("找不到CSV文件 '%s'。请检查路径是否正确。", filepath)
        return None
    except Exception as exc:
        logger.warning("估算行数失败: %s. 无法按百分比导入。", exc)
        return None


def process_chunk(
    chunk_data: pd.DataFrame,
    chunk_index: int,
    conn: psycopg2.extensions.connection,
    table_name: str,
    pbar,
    rows_counter,
    target_rows: Optional[int],
    pbar_unit: str,
):
    """
    描述：处理单个分块：预处理数据并写入数据库
    参数：chunk_data: 分块数据, chunk_index: 分块索引, conn: 数据库连接,
          table_name: 目标表名, pbar: 进度条, rows_counter: 计数器, target_rows: 目标行数, pbar_unit: 进度条单位
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
    chunk["trade_time"] = pd.to_datetime(chunk["trade_time"], unit="us", utc=True, errors="coerce")
    chunk.dropna(subset=["trade_time"], inplace=True)
    if chunk.empty:
        rows_counter[0] += original_chunk_len
        pbar.update(original_chunk_len if pbar_unit == "行" else 1)
        should_stop = target_rows is not None and rows_counter[0] >= target_rows
        return True, original_chunk_len, 0, should_stop
    try:
        csv_buffer = io.StringIO()
        chunk.to_csv(csv_buffer, index=False, header=False)
        csv_buffer.seek(0)
        columns = "id, price, qty, quote_qty, trade_time, is_buyer_maker, is_best_match"
        copy_sql = f"COPY {table_name} ({columns}) FROM STDIN WITH (FORMAT CSV)"
        with conn.cursor() as cursor:
            cursor.copy_expert(sql=copy_sql, file=csv_buffer)
        conn.commit()
        rows_imported = len(chunk)
        rows_counter[0] += original_chunk_len
        rows_counter[1] += rows_imported
        pbar.update(original_chunk_len if pbar_unit == "行" else 1)
        should_stop = target_rows is not None and rows_counter[0] >= target_rows
        return True, original_chunk_len, rows_imported, should_stop
    except Exception as db_err:
        logger.error("写入数据库块 %s 时失败: %s", chunk_index + 1, db_err)
        conn.rollback()
        rows_counter[0] += original_chunk_len
        pbar.update(original_chunk_len if pbar_unit == "行" else 1)
        should_stop = target_rows is not None and rows_counter[0] >= target_rows
        return False, original_chunk_len, 0, should_stop


def import_data_to_database(
    conn,
    target_rows: Optional[int],
    total_lines: Optional[int],
    csv_path: str,
    chunk_size: int,
    table_name: str,
    import_percentage: float,
):
    """
    描述：主导入逻辑：读取CSV，分块处理并写入数据库。
    """
    pbar_total = target_rows if target_rows is not None and import_percentage < 100 else total_lines
    pbar_unit = "行" if pbar_total is not None else "块"
    pbar = tqdm(total=pbar_total, unit=pbar_unit, desc="导入进度")
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
            _, _, _, stop_flag = process_chunk(
                chunk,
                i,
                conn,
                table_name,
                pbar,
                rows_counter,
                target_rows,
                pbar_unit,
            )
            if stop_flag and not should_stop:
                logger.info("已处理约 %s 行，达到目标 %s 行。", rows_counter[0], target_rows)
                should_stop = True
                break
    except FileNotFoundError:
        logger.error("找不到CSV文件 '%s'。请检查路径是否正确。", csv_path)
    except Exception as exc:
        logger.error("处理文件时发生意外错误: %s", exc)
        traceback.print_exc(file=sys.stderr)
    finally:
        pbar.close()
    return rows_counter


def _calc_target_rows(total_lines: Optional[int], import_percentage: float) -> Optional[int]:
    if total_lines is None:
        return None
    if import_percentage >= 100:
        return total_lines
    return math.ceil(total_lines * (import_percentage / 100))


def _build_db_conn(overrides: dict[str, Any]):
    cfg = DEFAULT_DB_CONFIG.copy()
    cfg.update(overrides or {})
    return psycopg2.connect(
        host=cfg.get("host"),
        port=cfg.get("port"),
        dbname=cfg.get("database"),
        user=cfg.get("username"),
        password=cfg.get("password"),
    )


def run_collect_binance(task_id: Optional[str] = None, config_json: Optional[str] = None):
    config = load_config_from_string(config_json)
    client = TaskClient(task_id)
    csv_path = config.get("csv_path", DEFAULT_CSV_FILE_PATH)
    import_percentage = float(config.get("import_percentage", DEFAULT_IMPORT_PERCENTAGE))
    chunk_size = int(config.get("chunk_size", DEFAULT_CHUNK_SIZE))
    table_name = config.get("table_name", "binance_trades")

    if not 0 <= import_percentage <= 100:
        raise ValueError("import_percentage 必须介于 0-100")

    client.update_status("running", f"开始导入数据: {csv_path}")

    total_lines = None
    if import_percentage < 100:
        total_lines = count_lines(csv_path)
        if total_lines is None:
            client.update_status("failed", "CSV 文件不存在")
            return

    target_rows = _calc_target_rows(total_lines, import_percentage)
    if target_rows:
        logger.info("计划导入 %s 行数据", target_rows)

    conn = None
    try:
        conn = _build_db_conn(config.get("db", {}))
        logger.info("数据库连接成功")
    except Exception as exc:
        client.update_status("failed", f"数据库连接失败: {exc}")
        raise

    try:
        start_time = time.time()
        rows_counter = import_data_to_database(
            conn,
            target_rows,
            total_lines,
            csv_path,
            chunk_size,
            table_name,
            import_percentage,
        )
        total_time = time.time() - start_time
        rows_imported = rows_counter[1]
        msg = f"成功导入 {rows_imported} 行，耗时 {total_time:.2f}s"
        logger.info(msg)
        client.update_status("success", msg, {"rows": rows_imported, "duration": total_time})
    except Exception as exc:
        client.update_status("failed", f"导入失败: {exc}")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                logger.error("数据库连接关闭失败")


def main():
    parser = argparse.ArgumentParser(description="导入 Binance aggTrades CSV 到数据库")
    parser.add_argument("--task-id", dest="task_id", help="任务 ID", default=None)
    parser.add_argument("--config", dest="config", help="JSON 格式配置", default=None)
    args = parser.parse_args()
    run_collect_binance(task_id=args.task_id, config_json=args.config)


if __name__ == "__main__":
    main()
