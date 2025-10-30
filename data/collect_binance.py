import io
import math
import sys
import time
import traceback

import pandas as pd
import psycopg2
import yaml
from loguru import logger
from tqdm import tqdm

# 修改成正确的文件路径
CSV_FILE_PATH = r"./ETHUSDT-trades-2025-09.csv"

# 从配置文件加载数据库配置
with open('config/config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)

HOST = config['db']['host']
PORT = config['db']['port']
DATABASE = config['db']['database']
USERNAME = config['db']['username']
PASSWORD = config['db']['password']

# 导入比例
IMPORT_PERCENTAGE = 1  # 整个6G的文件一共有1亿行
CHUNK_SIZE = 1_000_000
COLUMN_NAMES = ['id', 'price', 'qty', 'quoteQty', 'time', 'isBuyerMaker', 'isBestMatch']

# 为加速 pandas 解析，显式声明 dtype，避免类型推断
DTYPE_MAP = {
    'id': 'int64',
    'price': 'float64',
    'qty': 'float64',
    'quoteQty': 'float64',
    'time': 'int64',
    'isBuyerMaker': 'bool',
    'isBestMatch': 'bool',
}

# 检查导入百分比
if not 0 <= IMPORT_PERCENTAGE <= 100:
    logger.error("IMPORT_PERCENTAGE 必须在 0 到 100 之间。")
    sys.exit()

def count_lines(filepath):
    """
    描述：估算文件总行数，用于百分比导入控制
    参数：filepath: 文件路径
    返回值：文件总行数
    """
    try:
        logger.info("正在估算文件总行数")
        start_time = time.time()
        # 使用快速方式计数
        count = sum(1 for line in open(filepath, 'rb'))
        end_time = time.time()
        logger.info(f"估算完成，共约 {count} 行数据，耗时 {end_time - start_time:.2f} 秒。")
        return count
    except FileNotFoundError:
        logger.error(f"找不到CSV文件 '{filepath}'。请检查路径是否正确。")
        return None
    except Exception as e:
        logger.warning(f"估算行数失败: {e}. 无法按百分比导入。")
        return None

def process_chunk(chunk_data, chunk_index, conn, table_name, pbar,
                  rows_counter, target_rows, pbar_unit):
    """
    描述：处理单个分块：预处理数据并写入数据库
    参数：chunk_data: 分块数据, chunk_index: 分块索引, db_connection_string: 数据库连接字符串,
          table_name: 目标表名, pbar: 进度条, rows_counter: 计数器, target_rows: 目标行数, pbar_unit: 进度条单位
    返回值：成功标志, 处理行数, 导入行数, 是否停止标志
    """
    original_chunk_len = len(chunk_data)
    # 数据预处理
    chunk = chunk_data.copy()
    chunk.rename(columns={
        'time': 'trade_time', 'quoteQty': 'quote_qty',
        'isBuyerMaker': 'is_buyer_maker', 'isBestMatch': 'is_best_match'

    }, inplace=True)
    # 将微秒时间戳转换为 UTC datetime
    chunk['trade_time'] = pd.to_datetime(chunk['trade_time'], unit='us', utc=True, errors='coerce')
    chunk.dropna(subset=['trade_time'], inplace=True)
    if chunk.empty:
        rows_counter[0] += original_chunk_len
        pbar.update(original_chunk_len if pbar_unit == '行' else 1)
        should_stop = target_rows is not None and rows_counter[0] >= target_rows
        return (True, original_chunk_len, 0, should_stop)
    try:
        # 使用 psycopg2 COPY 批量导入
        csv_buffer = io.StringIO()
        # 以 CSV 无表头导出，Postgres COPY CSV 可识别 True/False 和 ISO8601 时间
        chunk.to_csv(csv_buffer, index=False, header=False)
        csv_buffer.seek(0)
        columns = (
            'id, price, qty, quote_qty, trade_time, is_buyer_maker, is_best_match'
        )
        copy_sql = f"COPY {table_name} ({columns}) FROM STDIN WITH (FORMAT CSV)"

        with conn.cursor() as cursor:
            cursor.copy_expert(sql=copy_sql, file=csv_buffer)

        conn.commit()
        rows_imported = len(chunk)
        rows_counter[0] += original_chunk_len
        rows_counter[1] += rows_imported
        pbar.update(original_chunk_len if pbar_unit == '行' else 1)
        should_stop = target_rows is not None and rows_counter[0] >= target_rows
        return (True, original_chunk_len, rows_imported, should_stop)

    except Exception as db_err:
        logger.error(f"写入数据库块 {chunk_index + 1} 时失败: {db_err}")
        conn.rollback()
        rows_counter[0] += original_chunk_len
        pbar.update(original_chunk_len if pbar_unit == '行' else 1)
        should_stop = target_rows is not None and rows_counter[0] >= target_rows
        return (False, original_chunk_len, 0, should_stop)

def import_data_to_database(conn, target_rows, total_lines):
    """
    描述：主导入逻辑：读取CSV，分块处理并写入数据库。
    参数：target_rows: 目标导入行数, total_lines: 文件总行数
    返回：[processed_rows_count, rows_imported_successfully]
    """
    # 准备 tqdm 进度条
    pbar_total = target_rows if target_rows is not None and IMPORT_PERCENTAGE < 100 else total_lines
    pbar_unit = '行' if pbar_total is not None else '块'
    pbar = tqdm(total=pbar_total, unit=pbar_unit, desc="导入进度")
    # 计数器：[processed_rows_count, rows_imported_successfully]
    rows_counter = [0, 0]

    try:
        # 流式读取分块并顺序 COPY
        logger.info("正在读取CSV文件分块并导入...")
        chunk_iterator = pd.read_csv(
            CSV_FILE_PATH,
            chunksize=CHUNK_SIZE,
            header=None,
            names=COLUMN_NAMES,
            usecols=COLUMN_NAMES,
            dtype=DTYPE_MAP,
            engine="c",
            low_memory=False,
            memory_map=True,
            on_bad_lines='skip'
        )
        should_stop = False
        for i, chunk in enumerate(chunk_iterator):
            success, rows_processed, rows_imported, stop_flag = process_chunk(
                chunk, i, conn, "binance_trades", pbar, rows_counter, target_rows, pbar_unit
            )
            if stop_flag and not should_stop:
                logger.info(f"已处理约 {rows_counter[0]} 行，达到目标 {target_rows} 行。")
                should_stop = True
                break
    except FileNotFoundError:
        logger.error(f"找不到CSV文件 '{CSV_FILE_PATH}'。请检查路径是否正确。")
        return rows_counter
    except Exception as e:
        logger.error(f"处理文件时发生意外错误: {e}")
        traceback.print_exc(file=sys.stderr)
        return rows_counter
    finally:
        pbar.close()
    return rows_counter

if __name__ == '__main__':
    # 估算行数并计算目标行数
    total_lines = None
    if IMPORT_PERCENTAGE < 100:
        total_lines = count_lines(CSV_FILE_PATH)
        if total_lines is None:
            # 如果文件不存在，退出
            if not CSV_FILE_PATH:
                sys.exit()
    target_rows = None
    if total_lines is not None and IMPORT_PERCENTAGE < 100:
        target_rows = math.ceil(total_lines * (IMPORT_PERCENTAGE / 100))
        logger.info(f"根据设置，将导入文件的前 {IMPORT_PERCENTAGE}%，约 {target_rows} 行数据。")
    elif total_lines is not None or IMPORT_PERCENTAGE == 100:
        target_rows = total_lines  # 导入全部
        logger.info("将导入整个文件。")
    # 初始化数据库连接
    try:
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            dbname=DATABASE,
            user=USERNAME,
            password=PASSWORD,
        )
        logger.info("数据库连接成功！")
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        sys.exit()

    # 执行数据导入
    logger.info(f"开始分块导入文件: {CSV_FILE_PATH} 到表 binance_trades")
    start_import_time = time.time()
    rows_counter = import_data_to_database(conn, target_rows, total_lines)
    end_import_time = time.time()
    total_time = end_import_time - start_import_time
    # 打印导入结果
    logger.info("文件导入过程结束！")
    rows_imported = rows_counter[1]
    if total_time > 0 and rows_imported > 0:
        logger.info(f"成功导入约 {rows_imported} 行数据。")
        logger.info(f"总耗时: {total_time:.2f} 秒。")
        logger.info(f"平均速度: {rows_imported / total_time:.0f} 行/秒")
    elif rows_imported == 0:
        logger.warning(f"没有数据被导入。请检查CSV文件路径、内容或数据库连接/权限。")
    else:
        logger.info(f"成功导入约 {rows_imported} 行数据。")
        logger.info(f"总耗时: {total_time:.2f} 秒。")
    try:
        conn.close()
    except Exception:
        logger.error("数据库连接关闭失败")