import time
from datetime import datetime, timezone

import pandas as pd
import psycopg2
import requests
import yaml
from loguru import logger
from psycopg2.extras import execute_values

# 1. 加载配置和常量
with open("config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Etherscan API 配置
# 使用您提供的API密钥。更好的实践是将其移至 config.yaml。
ETHERSCAN_API_KEY = config["etherscan"]["etherscan_api_key"]
ETHERSCAN_API_URL = config["etherscan"]["etherscan_api_url"]

# Uniswap 池地址 (WETH/USDT)
POOL_ADDRESS = config["etherscan"]["uniswap_pool_address"].lower()


# 数据库配置
HOST = config["db"]["host"]
PORT = config["db"]["port"]
DATABASE = config["db"]["database"]
USERNAME = config["db"]["username"]
PASSWORD = config["db"]["password"]


def setup_database_table(conn):
    """
    描述：创建 uniswap_swaps 表。
    参数：conn: 数据库连接
    """
    with conn.cursor() as cur:
        logger.info("正在准备数据库表 uniswap_swaps...")
        # 如果表不存在，则创建它
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uniswap_swaps (
                id SERIAL PRIMARY KEY,
                block_time TIMESTAMPTZ,
                price NUMERIC,
                amount_eth NUMERIC,
                amount_usdt NUMERIC,
                gas_price NUMERIC,
                tx_hash TEXT
            );
        """)
        conn.commit()


def get_block_by_timestamp(ts, closest="before"):
    """
    描述：使用Etherscan API，根据时间戳获取最接近的区块号
    参数：
        ts: Unix时间戳 (秒)
        closest: 'before' 或 'after'
    返回值：区块号 (str) 或 None
    """
    params = {
        "module": "block",
        "action": "getblocknobytime",
        "timestamp": ts,
        "closest": closest,
        "apikey": ETHERSCAN_API_KEY,
        "chainid": "1",  # 为V2 API添加chainid
    }
    logger.info(f"正在查询时间戳 {ts} 对应的区块号...")
    try:
        response = requests.get(ETHERSCAN_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "1":
            logger.info(f"查询成功，区块号: {data['result']}")
            return data["result"]
        else:
            logger.error(f"Etherscan API (getblocknobytime) 错误: {data['message']}")
            logger.error(f"Etherscan 完整响应: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"请求Etherscan API (getblocknobytime) 失败: {e}")
        return None


def fetch_swaps_from_etherscan(start_block, end_block):
    """
    描述：通过分页从Etherscan获取指定区块范围内的所有代币交易数据。
    参数：
        start_block: 起始区块号
        end_block: 终止区块号
    返回值：包含所有交易的列表
    """
    all_transactions = []
    page = 1
    offset = 1000  # Etherscan 推荐的 offset 值
    logger.info(f"开始从 Etherscan 获取区块 {start_block} 到 {end_block} 的数据...")
    while True:
        params = {
            "module": "account",
            "action": "tokentx",
            "address": POOL_ADDRESS,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": "asc",  # 按时间升序
            "apikey": ETHERSCAN_API_KEY,
            "chainid": "1",  # 为V2 API添加chainid
        }
        try:
            response = requests.get(ETHERSCAN_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if data["status"] != "1":
                # "0" 状态表示没有更多记录或API出错
                if data["message"] == "No transactions found":
                    logger.info("已获取所有分页数据。")
                else:
                    logger.error(f"Etherscan API (tokentx) 错误: {data['message']}")
                    logger.error(f"Etherscan 完整响应: {response.text}")
                break

            transactions = data["result"]
            if not transactions:
                logger.info("当前分页无数据，获取结束。")
                break

            all_transactions.extend(transactions)
            logger.info(f"已获取第 {page} 页数据，共 {len(all_transactions)} 条记录...")
            page += 1
            time.sleep(0.2)  # 遵守 Etherscan API 的速率限制 (5次/秒)

        except requests.exceptions.RequestException as e:
            logger.error(f"请求Etherscan API (tokentx) 失败: {e}。5秒后重试...")
            time.sleep(5)
            continue
    return all_transactions


def process_and_store_uniswap_data(raw_transactions, conn):
    """
    描述：处理从Etherscan获取的原始交易数据，计算价格并存入数据库。
    参数：
        raw_transactions：从 Etherscan API 获取的原始交易列表
        conn：数据库连接
    """
    if not raw_transactions:
        logger.info("没有获取到Etherscan数据。")
        return

    logger.info("正在处理Etherscan数据，将其按交易哈希分组...")
    df = pd.DataFrame(raw_transactions)
    # Etherscan 返回的值是字符串，需要转为数值
    # 使用 .astype(float) 来避免整数溢出，因为交易额（以wei为单位）可能非常大
    df["value"] = df["value"].astype(float)
    df["gasPrice"] = df["gasPrice"].astype(float)
    df["timeStamp"] = pd.to_numeric(df["timeStamp"])

    records = []
    grouped = df.groupby("hash")

    for tx_hash, group in grouped:
        weth_tx = group[group["tokenSymbol"] == "WETH"]
        usdt_tx = group[group["tokenSymbol"] == "USDT"]

        # 确保一个交易中同时包含WETH和USDT的转账
        if weth_tx.empty or usdt_tx.empty:
            continue

        # 通过对组内金额求和来处理复杂交易，这比 .iloc[0] 更健壮
        weth_total_value = weth_tx["value"].sum()
        usdt_total_value = usdt_tx["value"].sum()

        # 使用第一条记录来获取元数据，如时间戳和精度
        weth_row = weth_tx.iloc[0]
        usdt_row = usdt_tx.iloc[0]
        
        # 将代币数量从最小单位转换 (e.g., Gwei -> ETH)
        amount_eth_abs = weth_total_value / (10 ** int(weth_row["tokenDecimal"]))
        amount_usdt_abs = usdt_total_value / (10 ** int(usdt_row["tokenDecimal"]))

        # 根据转账方向确定数量的正负号（与collect_uniswap.py逻辑保持一致）
        # 这里我们假设一个交易内的所有同类代币转账方向是一致的
        # 即，要么都是流入池子，要么都是流出池子
        amount_eth = -amount_eth_abs if weth_row["to"] == POOL_ADDRESS else amount_eth_abs
        amount_usdt = -amount_usdt_abs if usdt_row["to"] == POOL_ADDRESS else amount_usdt_abs

        if amount_eth_abs == 0:
            continue

        price = amount_usdt_abs / amount_eth_abs

        records.append(
            {
                "block_time": pd.to_datetime(weth_row["timeStamp"], unit="s", utc=True),
                # 显式转换为 Python float 类型，避免 psycopg2 处理 numpy.float64 时可能出现的问题
                "price": float(price),
                "amount_eth": float(amount_eth),
                "amount_usdt": float(amount_usdt),
                "gas_price": int(weth_row["gasPrice"]),
                "tx_hash": tx_hash,
            }
        )

    logger.info(f"处理完成，共得到 {len(records)} 条有效Swap记录。")
    logger.info(f"正在将 {len(records)} 条Uniswap记录存入数据库...")
    
    with conn:
        with conn.cursor() as cur:
            insert_sql = (
                "INSERT INTO uniswap_swaps (block_time, price, amount_eth, amount_usdt, gas_price, tx_hash) "
                "VALUES %s"
            )
            values = [
                (
                    r["block_time"],
                    r["price"],
                    r["amount_eth"],
                    r["amount_usdt"],
                    r["gas_price"],
                    r["tx_hash"],
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

    # 准备数据库表，确保约束存在
    setup_database_table(conn)

    # 可以修改这里的日期来获取不同时间范围的数据
    # 注意：请使用过去的、真实存在的日期
    day_to_fetch = datetime(2025, 9, 2, 0, 0, 0, tzinfo=timezone.utc)
    logger.info(f"准备获取 {day_to_fetch.date()} 的Uniswap交易数据...")

    # 1. 根据时间范围确定起始和结束区块号
    start_ts = int(day_to_fetch.timestamp())
    end_ts = int((day_to_fetch + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).timestamp())
    
    start_block = get_block_by_timestamp(start_ts, closest="after")
    end_block = get_block_by_timestamp(end_ts, closest="before")

    if not start_block or not end_block:
        logger.error("未能获取到起始或结束区块号，程序退出。")
        conn.close()
    else:
        # 2. 获取原始交易数据
        raw_transactions = fetch_swaps_from_etherscan(start_block, end_block)
        
        # 3. 处理并存储数据
        process_and_store_uniswap_data(raw_transactions, conn)

    conn.close()
