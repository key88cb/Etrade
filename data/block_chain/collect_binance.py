import io
import math
import os
import sys
import tempfile
import time
import traceback
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pandas as pd
import psycopg2
import requests
import yaml
from loguru import logger

from .task import check_task, update_task_status

# 默认配置
with open("./config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

db_config = config.get("db", {})
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
        update_task_status(task_id, "FAILED")
        raise
    except Exception as e:
        logger.warning(f"估算行数失败: {e}. 无法按百分比导入。")
        update_task_status(task_id, "FAILED")
        raise


def process_chunk(
    task_id: str,
    chunk_data: pd.DataFrame,
    chunk_index: int,
    rows_counter,
    target_rows: Optional[int],
    conn: Optional[Any] = None,
):
    """
    描述：处理单个分块：预处理数据并写入数据库
    参数：task_id: 任务ID, chunk_data: 分块数据, chunk_index: 分块索引, rows_counter: 计数器, target_rows: 目标行数, conn: 数据库连接（可选）
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

        # 如果提供了连接，使用它；否则创建新连接
        if conn is not None:
            with conn.cursor() as cursor:
                cursor.copy_expert(sql=copy_sql, file=csv_buffer)
            # 不在这里提交，由调用者控制事务
        else:
            with psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                dbname=db_config["database"],
                user=db_config["username"],
                password=db_config["password"],
            ) as new_conn:
                with new_conn.cursor() as cursor:
                    cursor.copy_expert(sql=copy_sql, file=csv_buffer)
                new_conn.commit()
        rows_imported = len(chunk)
        rows_counter[0] += original_chunk_len
        rows_counter[1] += rows_imported
        should_stop = target_rows is not None and rows_counter[0] >= target_rows
        return True, original_chunk_len, rows_imported, should_stop
    except Exception as e:
        logger.error(f"处理分块时发生意外错误: {e}")
        update_task_status(task_id, "FAILED")
        raise


def import_data_to_database(
    task_id: str,
    csv_path: str,
    target_rows: Optional[int],
    total_lines: Optional[int],
    chunk_size: int,
    conn: Optional[Any] = None,
):
    """
    描述：主导入逻辑：读取CSV，分块处理并写入数据库。
    参数：target_rows: 目标行数, total_lines: 总行数, chunk_size: 分块大小, conn: 数据库连接（可选）
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
                conn,
            )
            if stop_flag and not should_stop:
                logger.info(
                    f"已处理约 {rows_counter[0]} 行，达到目标 {target_rows} 行。"
                )
                should_stop = True
                break
    except FileNotFoundError:
        logger.error(f"找不到CSV文件 '{csv_path}'。请检查路径是否正确。")
        update_task_status(task_id, "FAILED")
        raise
    except Exception as e:
        logger.error(f"处理文件时发生意外错误: {e}")
        traceback.print_exc(file=sys.stderr)
        update_task_status(task_id, "FAILED")
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
    """
    描述：收集 Binance 数据（作为事务处理，如果任务取消则完全回滚）
    参数：
        task_id: 任务ID
        csv_path: CSV文件路径
        import_percentage: 导入百分比
        chunk_size: 分块大小
    返回值：导入的总行数
    """
    conn = None
    try:
        start_time = time.time()
        total_lines = count_lines(task_id, csv_path)
        if check_task(task_id):
            logger.info(f"任务 {task_id} 已取消，停止导入 Binance 数据")
            return 0

        # 创建数据库连接并开始事务
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            dbname=db_config["database"],
            user=db_config["username"],
            password=db_config["password"],
        )
        conn.autocommit = False  # 禁用自动提交，使用事务
        logger.info("已开启数据库事务，所有导入操作将在事务中执行")

        target_rows = _calc_target_rows(total_lines, import_percentage)
        rows_counter = import_data_to_database(
            task_id, csv_path, target_rows, total_lines, chunk_size, conn
        )
        total_time = time.time() - start_time

        if check_task(task_id):
            logger.info(f"任务 {task_id} 已取消，回滚所有已导入的数据")
            conn.rollback()
            logger.info("已回滚所有数据")
            return 0

        # 所有数据导入成功，提交事务
        conn.commit()
        logger.info("事务已提交，所有数据已成功导入")
        logger.info(f"成功导入 {rows_counter[1]} 行，耗时 {total_time:.2f}s")
        update_task_status(task_id, "SUCCESS")
        return rows_counter[1]
    except Exception as e:
        logger.error(f"导入 Binance 数据失败: {e}")
        traceback.print_exc(file=sys.stderr)
        # 确保在异常情况下回滚事务
        if conn is not None:
            try:
                conn.rollback()
                logger.info("发生异常，已回滚所有数据")
            except Exception as rollback_error:
                logger.error(f"回滚事务失败: {rollback_error}")
        update_task_status(task_id, "FAILED")
        raise
    finally:
        # 确保关闭数据库连接
        if conn is not None:
            try:
                conn.close()
            except Exception as close_error:
                logger.warning(f"关闭数据库连接失败: {close_error}")


def download_binance_file(
    task_id: str, date_str: str, symbol: str = "ETHUSDT"
) -> Optional[str]:
    """
    描述：从币安数据源下载指定日期的交易数据文件
    参数：task_id: 任务ID, date_str: 日期字符串 (YYYY-MM-DD), symbol: 交易对符号
    返回值：下载的CSV文件路径，如果失败返回None
    """
    base_url = "https://data.binance.vision/data/spot/daily/trades"
    url = f"{base_url}/{symbol}/{symbol}-trades-{date_str}.zip"

    try:
        logger.info(f"正在下载币安数据: {url}")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        # 创建临时目录保存文件
        temp_dir = tempfile.mkdtemp(prefix="binance_")
        zip_path = os.path.join(temp_dir, f"{symbol}-trades-{date_str}.zip")

        # 下载zip文件
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    if check_task(task_id):
                        logger.info(f"任务 {task_id} 已取消，停止下载")
                        os.remove(zip_path)
                        os.rmdir(temp_dir)
                        return None

        # 解压文件
        csv_path = None
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # 获取zip文件中的CSV文件名
            csv_files = [f for f in zip_ref.namelist() if f.endswith(".csv")]
            if not csv_files:
                logger.error(f"ZIP文件中没有找到CSV文件: {zip_path}")
                os.remove(zip_path)
                os.rmdir(temp_dir)
                return None

            # 解压第一个CSV文件
            csv_filename = csv_files[0]
            zip_ref.extract(csv_filename, temp_dir)
            csv_path = os.path.join(temp_dir, csv_filename)

        # 删除zip文件
        os.remove(zip_path)
        logger.info(f"成功下载并解压: {csv_path}")
        return csv_path

    except requests.exceptions.RequestException as e:
        logger.error(f"下载币安数据失败: {e}")
        return None
    except zipfile.BadZipFile as e:
        logger.error(f"解压文件失败: {e}")
        return None
    except Exception as e:
        logger.error(f"处理文件时发生错误: {e}")
        return None


def collect_binance_by_date(
    task_id: str,
    start_ts: int,
    end_ts: int,
    symbol: str = "ETHUSDT",
    chunk_size: int = 1000000,
) -> int:
    """
    描述：按日期范围收集币安数据（作为事务处理，如果任务取消则完全回滚）
    参数：
        task_id: 任务ID
        start_ts: 起始时间戳（秒级）
        end_ts: 终止时间戳（秒级）
        symbol: 交易对符号，默认为ETHUSDT
        chunk_size: 分块大小，默认1000000
    返回值：导入的总行数
    """
    conn = None
    try:
        start_time = time.time()

        # 将时间戳转换为日期
        start_date = datetime.fromtimestamp(start_ts, tz=timezone.utc)
        end_date = datetime.fromtimestamp(end_ts, tz=timezone.utc)

        logger.info(f"开始按日期收集币安数据: {start_date.date()} 到 {end_date.date()}")

        # 创建数据库连接并开始事务
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            dbname=db_config["database"],
            user=db_config["username"],
            password=db_config["password"],
        )
        conn.autocommit = False  # 禁用自动提交，使用事务
        logger.info("已开启数据库事务，所有导入操作将在事务中执行")

        total_rows_imported = 0
        temp_files = []  # 记录临时文件，用于清理

        # 遍历日期范围
        current_date = start_date.date()
        end_date_only = end_date.date()

        while current_date <= end_date_only:
            if check_task(task_id):
                logger.info(f"任务 {task_id} 已取消，回滚所有已导入的数据")
                conn.rollback()
                logger.info("已回滚所有数据")
                return 0

            date_str = current_date.strftime("%Y-%m-%d")
            logger.info(f"正在处理日期: {date_str}")

            # 下载文件
            csv_path = download_binance_file(task_id, date_str, symbol)

            if csv_path is None:
                logger.warning(f"跳过日期 {date_str}，下载失败")
                current_date += timedelta(days=1)
                continue

            temp_files.append(csv_path)
            temp_files.append(os.path.dirname(csv_path))  # 临时目录

            try:
                # 导入数据（导入全部数据，不限制百分比）
                # 使用共享的数据库连接，所有操作在同一事务中
                rows_counter = import_data_to_database(
                    task_id, csv_path, None, None, chunk_size, conn
                )
                total_rows_imported += rows_counter[1]
                logger.info(f"日期 {date_str} 导入完成，导入 {rows_counter[1]} 行")
            except Exception as e:
                logger.error(f"导入日期 {date_str} 的数据失败: {e}")
                # 发生错误，回滚事务
                conn.rollback()
                logger.error("已回滚所有数据")
                raise

            # 清理临时文件
            try:
                if os.path.exists(csv_path):
                    os.remove(csv_path)
                temp_dir = os.path.dirname(csv_path)
                if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

            current_date += timedelta(days=1)

        total_time = time.time() - start_time

        if check_task(task_id):
            logger.info(f"任务 {task_id} 已取消，回滚所有已导入的数据")
            conn.rollback()
            logger.info("已回滚所有数据")
            return 0

        # 所有数据导入成功，提交事务
        conn.commit()
        logger.info("事务已提交，所有数据已成功导入")

        logger.info(f"成功导入 {total_rows_imported} 行，耗时 {total_time:.2f}s")
        update_task_status(task_id, "SUCCESS")
        return total_rows_imported

    except Exception as e:
        logger.error(f"按日期收集 Binance 数据失败: {e}")
        traceback.print_exc(file=sys.stderr)
        # 确保在异常情况下回滚事务
        if conn is not None:
            try:
                conn.rollback()
                logger.info("发生异常，已回滚所有数据")
            except Exception as rollback_error:
                logger.error(f"回滚事务失败: {rollback_error}")
        update_task_status(task_id, "FAILED")
        raise
    finally:
        # 确保关闭数据库连接
        if conn is not None:
            try:
                conn.close()
            except Exception as close_error:
                logger.warning(f"关闭数据库连接失败: {close_error}")


if __name__ == "__main__":
    collect_binance("1", "./ETHUSDT-trades-2025-12-23.csv", 1, 1000000)
