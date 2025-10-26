import requests
import pandas as pd
from sqlalchemy import create_engine
import time
import os

from dotenv import load_dotenv

load_dotenv()

# 替换成从The Graph Studio获取的、包含API Key的完整URL
THE_GRAPH_API_URL = os.getenv(
    "THE_GRAPH_API_URL",
    "https://gateway.thegraph.com/api/YOURAPIKEY/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
)
POOL_ADDRESS = os.getenv(
    "UNISWAP_POOL_ADDRESS",
    "0x11b815efb8f581194ae79006d24e0d814b7697f6"
)

# 数据库连接字符串
DB_CONNECTION_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/etrade"
)

# 时间范围: 2025-09-01
START_TIMESTAMP = 1756694400  # 2025-09-01 00:00:00 UTC
END_TIMESTAMP = 1756780799  # 截止自己定


def fetch_all_swaps(pool_address, start_ts, end_ts):
    """通过分页获取指定时间范围内的所有Swap数据。"""
    all_swaps = []
    last_id = ""  # 使用 last_id 进行分页，更稳定

    print(f"开始从 The Graph 获取 Uniswap 数据...")

    while True:
        # id_gt 表示获取 id 大于 last_id 的记录
        # graphQL api 是fb的新范式 会直接返回对应名字的数据 可以把下面的查询当做一个空json
        query = """
        {
          swaps(
            first: 1000,
            orderBy: id,
            orderDirection: asc,
            where: {
              pool: "%s",
              timestamp_gte: %d,
              timestamp_lte: %d,
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
        """ % (pool_address, start_ts, end_ts, last_id)

        try:
            response = requests.post(THE_GRAPH_API_URL, json={'query': query})
            response.raise_for_status()  # 如果请求失败则抛出异常
            raw_data = response.json()

            swaps = response.json()['data']['swaps']
        except (requests.exceptions.RequestException, KeyError) as e:
            print(f"请求失败: {e}。5秒后重试...")
            time.sleep(5)
            continue

        if not swaps:
            break

        all_swaps.extend(swaps)
        last_id = swaps[-1]['id']

        print(f"已获取 {len(all_swaps)} 条记录...")
        time.sleep(1)

    return all_swaps


def process_and_store_uniswap_data(swaps_data, engine):
    """处理数据并存入数据库。"""
    if not swaps_data:
        print("没有获取到Uniswap数据。")
        return

    print("正在处理Uniswap数据...")

    records = []
    for s in swaps_data:
        amount0 = float(s['amount0'])
        amount1 = float(s['amount1'])

        if amount0 == 0: continue  # 避免除以零错误

        price = abs(amount1 / amount0)

        records.append({
            'block_time': pd.to_datetime(s['timestamp'], unit='s', utc=True),
            'price': price,
            'amount_eth': amount0,  # WETH是token0
            'amount_usdt': amount1,
            'gas_price': int(s['transaction']['gasPrice']),
            'tx_hash': s['transaction']['id']
        })

    df = pd.DataFrame(records)

    print(f"正在将 {len(df)} 条Uniswap记录存入数据库...")
    # 注意：表名 `uniswap_swaps` 必须与Go后端模型迁移后的表名完全一致
    df.to_sql('uniswap_swaps', engine, if_exists='replace', index=False)
    print("Uniswap数据存储成功！")


if __name__ == "__main__":
    engine = create_engine(DB_CONNECTION_STRING)
    all_swaps = fetch_all_swaps(POOL_ADDRESS, START_TIMESTAMP, END_TIMESTAMP)
    process_and_store_uniswap_data(all_swaps, engine)
