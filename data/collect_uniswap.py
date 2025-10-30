import threading
import time
from datetime import datetime, timezone

import pandas as pd
import psycopg2
import requests
import yaml
from loguru import logger
from psycopg2.extras import execute_values

with open('config/config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)

API_KEY = config['the_graph']['api_key']
GRAPH_API_URL = config['the_graph']['graph_api_url']
POOL_ADDRESS = config['the_graph']['uniswap_pool_address']
HOST = config['db']['host']
PORT = config['db']['port']
DATABASE = config['db']['database']
USERNAME = config['db']['username']
PASSWORD = config['db']['password']
DB_CONNECTION_STRING = f'postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}'

def fetch_all_swaps(pool_address, start_ts, end_ts):
    """
    描述：通过分页获取指定时间范围内的所有Swap数据。
    参数：
        pool_address：池地址
        start_ts：起始时间的Unix时间戳（秒级）
        end_ts：终止时间的Uninx时间戳（秒级）
    返回值：获取到的uniswap数据
    """
    all_swaps = []
    last_id = ""  # 使用 last_id 进行分页，更稳定
    logger.info(f"开始从 The Graph 获取 Uniswap 数据...")
    while True:
        # id_gt 表示获取 id 大于 last_id 的记录
        # graphQL api 是fb的新范式 会直接返回对应名字的数据 可以把下面的查询当做一个空json
        query = """
        query GetRecentSwaps {
        swaps(
            first: 1000,
            orderBy: id
            orderDirection: asc
            where: {
            pool: "0x%lx"
            timestamp_gte: %d
            timestamp_lte: %d
            id_gt: "%s"
            }
        ) {
            id
            timestamp
            amount0
            amount1
            transaction {
            id
            gasPrice
            }
        }
        }
        """%(POOL_ADDRESS, start_ts, end_ts, last_id)

        try:
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            response = requests.post(GRAPH_API_URL, json={'query': query}, headers=headers)
            response.raise_for_status()  # 如果请求失败则抛出异常
            swaps = response.json()['data']['swaps']
        except (requests.exceptions.RequestException, KeyError) as e:
            logger.info(f"请求失败: {e}。5秒后重试...")
            logger.error(f"请求失败: {response.text}")
            time.sleep(5)
            continue

        if not swaps:
            break

        all_swaps.extend(swaps)
        last_id = swaps[-1]['id']
        logger.info(f"last id = {last_id}")
        logger.info(f"已获取 {len(all_swaps)} 条记录...")
        time.sleep(1)
    return all_swaps

def process_and_store_uniswap_data(swaps_data, conn):
    """
    描述：处理数据并存入数据库。
    参数：
        swaps_data：爬取到的 swap 数据
        conn：数据库连接
    """
    if not swaps_data:
        logger.info("没有获取到Uniswap数据。")
        return
    
    logger.info("正在处理Uniswap数据...")
    records = []
    for s in swaps_data:
        amount0 = float(s['amount0'])
        amount1 = float(s['amount1'])
        if amount0 == 0: continue  # 避免除以零错误
        price = abs(amount1 / amount0)
        records.append({
            'block_time': pd.to_datetime(pd.to_numeric(s['timestamp'], errors='coerce'), unit='s', utc=True),
            'price': price,
            'amount_eth': amount0,  # WETH是token0
            'amount_usdt': amount1,
            'gas_price': int(s['transaction']['gasPrice']),
            'tx_hash': s['transaction']['id']
        })
    logger.info(f"正在将 {len(records)} 条Uniswap记录存入数据库...")
    with conn:
        with conn.cursor() as cur:
            insert_sql = (
                "INSERT INTO uniswap_swaps (block_time, price, amount_eth, amount_usdt, gas_price, tx_hash) "
                "VALUES %s"
            )
            values = [
                (
                    r['block_time'].to_pydatetime(),
                    r['price'],
                    r['amount_eth'],
                    r['amount_usdt'],
                    r['gas_price'],
                    r['tx_hash']
                )
                for r in records
            ]
            if values:
                execute_values(cur, insert_sql, values, page_size=1000)
    logger.info("Uniswap数据存储成功！")

if __name__ == "__main__":
    conn = psycopg2.connect(
        dbname=DATABASE,
        user=USERNAME,
        password=PASSWORD,
        host=HOST,
        port=PORT,
    )
    # 输入时间范围 2025-9-x ~ 2025-9-y
    for i in range(2, 3):
        logger.info(f"目前处理到 2025-9-{i}")
        start_time = datetime(2025, 9, i, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 9, i, 23, 59, 59, tzinfo=timezone.utc)
        all_swaps = fetch_all_swaps(POOL_ADDRESS, start_time.timestamp(), end_time.timestamp())
        process_and_store_uniswap_data(all_swaps, conn)

    conn.close()