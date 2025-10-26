import pandas as pd
from sqlalchemy import create_engine,text
import time
from tqdm import tqdm
import math
import sys
import os

from dotenv import load_dotenv

load_dotenv()

# --- 1. 配置 (!!! 请务必修改为你自己的信息 !!!) ---
CSV_FILE_PATH = r"D:\大三上\SRE软件需求工程\ETHUSDT-trades-2025-09\ETHUSDT-trades-2025-09.csv"
DB_CONNECTION_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/etrade"
)
TABLE_NAME = "binance_trades"

# 设置为 100 则导入整个文件。
# 设置为 10 只会导入前 10% 的数据。
IMPORT_PERCENTAGE = 3  # 整个6G的文件一共有1亿行 很多很多 这个数字还是较为合理的

# --- 分块大小 ---
CHUNK_SIZE = 1_000_000

# --- CSV列名 ---
COLUMN_NAMES = ['id', 'price', 'qty', 'quoteQty', 'time', 'isBuyerMaker', 'isBestMatch']

if not 0 <= IMPORT_PERCENTAGE <= 100:
    print("错误：IMPORT_PERCENTAGE 必须在 0 到 100 之间。")
    sys.exit()


# --- 3. 估算总行数 ---
def count_lines(filepath):
    """快速估算文件行数 (假设第一行是特殊行或表头)"""
    try:
        print("正在估算文件总行数 (这可能需要一点时间)...")
        start_time = time.time()
        with open(filepath, 'rb') as f:
            count = sum(1 for line in f)
        end_time = time.time()
        # 假设文件第一行是表头或无效数据
        actual_data_lines = count - 1 if count > 0 else 0
        print(f"估算完成，共约 {actual_data_lines} 行数据，耗时 {end_time - start_time:.2f} 秒。")
        return actual_data_lines
    except FileNotFoundError:
        print(f"\n错误：找不到CSV文件 '{filepath}'。请检查路径是否正确。")
        return None  # 返回 None 表示失败
    except Exception as e:
        print(f"估算行数失败: {e}. 无法按百分比导入。将尝试导入整个文件。")
        return None


total_lines = count_lines(CSV_FILE_PATH)

# 如果找不到文件，则退出
if total_lines is None and not CSV_FILE_PATH:  # Check added for clarity
    sys.exit()

# --- 4. 计算目标行数 ---
target_rows = None
if total_lines is not None and IMPORT_PERCENTAGE < 100:
    target_rows = math.ceil(total_lines * (IMPORT_PERCENTAGE / 100))
    print(f"根据设置，将导入文件的前 {IMPORT_PERCENTAGE}%，约 {target_rows} 行数据。")
elif total_lines is not None:
    target_rows = total_lines  # 导入全部
    print("将导入整个文件。")
# else: total_lines is None, 无法计算百分比，后面会处理整个文件

# --- 5. 初始化数据库连接 ---
try:
    engine = create_engine(DB_CONNECTION_STRING)
    with engine.connect() as connection:
        print("数据库连接成功！")
except Exception as e:
    print(f"数据库连接失败: {e}")
    sys.exit()

# --- 6. 询问用户是否清空表 ---
user_input = input(f"警告：即将开始导入数据到表 '{TABLE_NAME}'。\n"
                   f"是否要在导入前清空该表？(输入 'yes' 清空，其他任意键跳过): ").strip().lower()

if user_input == 'yes':
    try:
        print(f"正在清空表 '{TABLE_NAME}'...")
        with engine.begin() as connection: # 使用事务确保安全
            connection.execute(text(f"TRUNCATE TABLE {TABLE_NAME};"))
        print("表已清空。")
    except Exception as e:
        print(f"清空表失败: {e}")
        print("请手动清空表或检查表名和权限。")
        sys.exit()

# --- 7. 分块读取并写入数据库 ---
print(f"\n开始分块导入文件: {CSV_FILE_PATH} 到表 {TABLE_NAME}")
start_import_time = time.time()

# 准备 tqdm 进度条
pbar_total = target_rows if target_rows is not None and IMPORT_PERCENTAGE < 100 else total_lines
pbar_unit = '行' if pbar_total is not None else '块'
pbar = tqdm(total=pbar_total, unit=pbar_unit, desc="导入进度")

rows_imported_successfully = 0
processed_rows_count = 0  # 记录读取的总行数（用于百分比判断）

try:
    chunk_iterator = pd.read_csv(
        CSV_FILE_PATH,
        chunksize=CHUNK_SIZE,
        header=None,
        names=COLUMN_NAMES
    )

    for i, chunk in enumerate(chunk_iterator):
        original_chunk_len = len(chunk)  # 记录原始块大小，用于进度条
        processed_rows_count += original_chunk_len  # 累加读取的行数

        # --- 数据预处理 ---
        chunk.rename(columns={
            'time': 'trade_time', 'quoteQty': 'quote_qty',
            'isBuyerMaker': 'is_buyer_maker', 'isBestMatch': 'is_best_match'
        }, inplace=True)
        chunk['trade_time'] = pd.to_datetime(chunk['trade_time'], unit='us', utc=True, errors='coerce')  # 确认单位是 us
        chunk.dropna(subset=['trade_time'], inplace=True)

        if chunk.empty:
            # 即使块为空也要更新进度条，确保它能最终到达 total
            pbar.update(original_chunk_len if pbar_unit == '行' else 1)
            # 检查是否已达到目标（即使块为空也可能达到）
            if target_rows is not None and processed_rows_count >= target_rows:
                print(f"\n已读取约 {processed_rows_count} 行，达到目标 {target_rows} 行，停止导入。")
                break
            continue

        # --- 写入数据库 ---
        try:
            chunk.to_sql(TABLE_NAME, engine, if_exists='append', index=False, method='multi', chunksize=10000)
            rows_imported_successfully += len(chunk)
            # 更新进度条
            pbar.update(original_chunk_len if pbar_unit == '行' else 1)

        except Exception as db_err:
            print(f"\n错误：写入数据库块 {i + 1} 时失败: {db_err}")
            print(f"跳过块 {i + 1} 的写入。")
            pbar.update(original_chunk_len if pbar_unit == '行' else 1)  # 即使失败也要更新进度
            # 检查是否已达到目标（即使写入失败也可能达到读取目标）
            if target_rows is not None and processed_rows_count >= target_rows:
                print(f"\n已读取约 {processed_rows_count} 行，达到目标 {target_rows} 行，停止导入。")
                break
            continue

            # --- 检查是否达到目标行数 ---
        # 在成功写入一个块之后检查
        if target_rows is not None and processed_rows_count >= target_rows:
            print(f"\n已读取约 {processed_rows_count} 行，达到目标 {target_rows} 行，停止导入。")
            break  # 退出循环

except FileNotFoundError:
    print(f"\n错误：找不到CSV文件 '{CSV_FILE_PATH}'。请检查路径是否正确。")
except Exception as e:
    print(f"\n处理文件时发生意外错误: {e}")

finally:
    pbar.close()

end_import_time = time.time()
total_time = end_import_time - start_import_time
print(f"\n文件导入过程结束！")
print(f"成功导入约 {rows_imported_successfully} 行数据。")
print(f"总耗时: {total_time:.2f} 秒。")
