import requests
import pandas as pd
from sqlalchemy import create_engine
import time
import datetime
import concurrent.futures
import random

# --- 修正后的配置 ---
BINANCE_API_URL = "https://api.binance.com"
SYMBOL = "ETHUSDT"
MAX_WORKERS = 2  # <-- 降低并发数

DB_CONNECTION_STRING = "postgresql://postgres:mysecretpassword@localhost:5432/etrade"

# 【重要提醒】请使用真实的历史数据年份
YEAR = 2025
MONTH = 9
DAY = 1


def fetch_chunk(symbol, start_time_ms, end_time_ms):
    """获取一个指定小时间块内的所有aggTrades数据。"""
    chunk_trades = []
    current_start_time = start_time_ms
    thread_name = f"Thread-{start_time_ms}"
    print(f"[{thread_name}] 开始获取时间段: {start_time_ms} -> {end_time_ms}")

    while current_start_time < end_time_ms:
        try:
            response = requests.get(
                f"{BINANCE_API_URL}/api/v3/aggTrades",
                params={'symbol': symbol, 'startTime': current_start_time, 'endTime': end_time_ms, 'limit': 1000},
                timeout=(5, 15)  # <-- 【新增】设置超时
            )
            response.raise_for_status()
            trades = response.json()
        except requests.exceptions.RequestException as e:
            print(f"[{thread_name}] 请求失败: {e}。将重试...")
            time.sleep(5)
            continue

        if not trades:
            break

        chunk_trades.extend(trades)
        last_trade_time = trades[-1]['T']

        if last_trade_time >= current_start_time:
            current_start_time = last_trade_time + 1
        else:
            break

        time.sleep(random.uniform(0.1, 0.3))

    print(f"[{thread_name}] 完成获取，共 {len(chunk_trades)} 条记录。")
    return chunk_trades
def process_and_store_binance_data(trades_data, engine):
    if not trades_data:
        print("列表中没有任何数据可以保存。")
        return

    print(f"\n正在处理 {len(trades_data)} 条已获取的币安数据...")
    df = pd.DataFrame(trades_data)
    df_renamed = df[['T', 'p', 'q']].rename(columns={
        'T': 'trade_time',
        'p': 'price',
        'q': 'quantity'
    })

    df_renamed['trade_time'] = pd.to_datetime(df_renamed['trade_time'], unit='ms', utc=True)
    df_renamed['price'] = pd.to_numeric(df_renamed['price'])
    df_renamed['quantity'] = pd.to_numeric(df_renamed['quantity'])

    df_renamed.drop_duplicates(subset=['trade_time', 'price', 'quantity'], inplace=True)

    print(f"正在将 {len(df_renamed)} 条不重复的币安记录存入数据库...")
    df_renamed.to_sql('binance_trades', engine, if_exists='replace', index=False)
    print("币安数据存储成功！")


if __name__ == "__main__":
    tasks = []
    day_start = datetime.datetime(YEAR, MONTH, DAY, 0, 0, 0, tzinfo=datetime.timezone.utc)
    for hour in range(12):
        chunk_start_dt = day_start + datetime.timedelta(hours=hour)
        chunk_end_dt = day_start + datetime.timedelta(hours=hour + 1) - datetime.timedelta(milliseconds=1)
        start_ms = int(chunk_start_dt.timestamp() * 1000)
        end_ms = int(chunk_end_dt.timestamp() * 1000)
        tasks.append((start_ms, end_ms))

    all_trades = []

    try:
        # 使用线程池并发执行 有可能会出访问过于频繁而被限流的情况 单线程会有些慢
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_chunk = {executor.submit(fetch_chunk, SYMBOL, start, end): (start, end) for start, end in tasks}

            # as_completed 会在每个任务完成时立即返回结果
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_info = future_to_chunk[future]
                try:
                    chunk_result = future.result()
                    if chunk_result:
                        all_trades.extend(chunk_result)
                        print(f"主线程：已收集 {len(all_trades)} 条总记录。")
                except Exception as exc:
                    print(f'时间段 {chunk_info} 在执行中产生了一个异常: {exc}')

    except KeyboardInterrupt:
        print("\n捕获到中断信号 (Ctrl+C) 保存已获取的数据...")

    finally:
        print("\n--- 进入数据保存阶段 ---")
        engine = create_engine(DB_CONNECTION_STRING)
        process_and_store_binance_data(all_trades, engine)