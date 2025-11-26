import argparse
from typing import Optional, Tuple

import pandas as pd
import psycopg2
import yaml
from loguru import logger
from psycopg2.extras import execute_values

# 1. 定义常量
# 交易成本
BINANCE_FEE_RATE = 0.001  # 币安吃单费率
UNISWAP_FEE_RATE = 0.0005  # Uniswap池费率
ESTIMATED_GAS_USED = 20  # Gas消耗量估算值

# 策略参数
INITIAL_INVESTMENT_USDT = 100000.0  # 每次套利的初始投入资金
TIME_DELAY_SECONDS = 3  # 非原子套利的执行延迟估算 (6秒)
PROFIT_THRESHOLD_USDT = 10  # 只记录利润大于1 USDT的机会
# 2. 数据库连接 (psycopg2)
with open("config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)
    HOST = config["db"]["host"]
    PORT = config["db"]["port"]
    DATABASE = config["db"]["database"]
    USERNAME = config["db"]["username"]
    PASSWORD = config["db"]["password"]

conn = psycopg2.connect(
    host=HOST,
    port=PORT,
    dbname=DATABASE,
    user=USERNAME,
    password=PASSWORD,
)
conn.autocommit = False
cur = conn.cursor()


def parse_cli_args() -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    parser = argparse.ArgumentParser(
        description="从数据库中筛选指定时间范围的交易数据并执行套利分析。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--start",
        type=str,
        help="起始时间 (ISO8601，如 2025-09-01T00:00:00Z)。若未提供，则从最早数据开始。",
    )
    parser.add_argument(
        "--end",
        type=str,
        help="结束时间 (ISO8601，如 2025-09-07T23:59:59Z)。若未提供，则一直到最新数据。",
    )
    args = parser.parse_args()

    def to_timestamp(value: Optional[str]) -> Optional[pd.Timestamp]:
        if not value:
            return None
        ts = pd.to_datetime(value, utc=True, errors="raise")
        return ts

    start_ts = to_timestamp(args.start)
    end_ts = to_timestamp(args.end)

    if start_ts and end_ts and start_ts > end_ts:
        parser.error("参数错误：start 时间必须早于 end 时间。")

    return start_ts, end_ts


def fetch_price_pairs(
    start_time: Optional[pd.Timestamp] = None, end_time: Optional[pd.Timestamp] = None
) -> list:
    """
    使用单个 SQL JOIN 查询，让数据库服务器完成所有繁重的计算
    (匹配和求平均值)，只返回最终需要的数据对。
    """
    logger.info("正在请求服务器计算并返回所有价格对...")
    time_range_msg = "全量数据"
    if start_time or end_time:
        time_range_msg = f"{start_time or '最早'} -> {end_time or '最新'}"
    logger.info(f"筛选时间范围：{time_range_msg}")

    # SQL 查询的参数
    # 1. 将 Python 变量传入 SQL
    params = {
        "delay_seconds": f"{TIME_DELAY_SECONDS} seconds",
        "window_seconds": "5 seconds",  # 窗口是 +/- 5秒
        "start_ts": start_time.to_pydatetime() if start_time else None,
        "end_ts": end_time.to_pydatetime() if end_time else None,
    }

    # 2. 构建 WHERE 子句
    time_conditions = []
    if params["start_ts"]:
        time_conditions.append("u.block_time >= %(start_ts)s")
    if params["end_ts"]:
        time_conditions.append("u.block_time <= %(end_ts)s")

    # 如果没有时间范围，则删除键以避免SQL错误
    if not time_conditions:
        if "start_ts" in params:
            del params["start_ts"]
        if "end_ts" in params:
            del params["end_ts"]

    where_clause = f"WHERE {' AND '.join(time_conditions)}" if time_conditions else ""

    # 3. 终极 SQL 查询
    # 使用 CTEs (Common Table Expressions) 来提高可读性
    # 并使用 JOIN ... GROUP BY 来计算币安的平均价格
    sql_query = f"""
        WITH 
        config AS (
            -- 1. 定义我们的常量
            SELECT 
                %(delay_seconds)s::interval AS delay,
                %(window_seconds)s::interval AS window
        ),
        uniswap_data AS (
            -- 2. 筛选 Uniswap 数据
            SELECT 
                block_time, 
                price AS uniswap_price, 
                gas_price
            FROM uniswap_swaps u
            {where_clause}
        ),
        binance_avg AS (
            -- 3. [核心] JOIN 两个表并计算币安平均价格
            -- 这会利用两个表上的时间索引，速度非常快
            SELECT 
                u.block_time,
                AVG(b.price) AS binance_price
            FROM 
                uniswap_data u
            CROSS JOIN -- (与 config 表交叉连接)
                config c 
            JOIN 
                binance_trades b 
            ON 
                b.trade_time BETWEEN 
                    (u.block_time - c.delay - c.window) -- <--- 修改这里
                AND 
                    (u.block_time - c.delay + c.window) -- <--- 修改这里
            GROUP BY 
                u.block_time
        )
        -- 4. 最终将所有需要的数据组合在一起
        SELECT 
            u.block_time,
            u.uniswap_price,
            u.gas_price,
            b.binance_price
        FROM 
            uniswap_data u
        JOIN 
            binance_avg b ON u.block_time = b.block_time
        ORDER BY
            u.block_time;
    """

    logger.info("正在执行服务器端计算... (这可能需要几秒钟)")
    cur.execute(sql_query, params)
    price_pairs = cur.fetchall()
    logger.info(f"计算完成，从服务器收到 {len(price_pairs)} 对价格。")

    return price_pairs


def calculate_profit_buy_cex_sell_dex(investment, price_cex, price_dex, gas_price):
    eth_acquired = (investment * (1 - BINANCE_FEE_RATE)) / price_cex
    gross_revenue_usdt = eth_acquired * price_dex
    uniswap_fee = gross_revenue_usdt * UNISWAP_FEE_RATE

    gas_cost_eth = (ESTIMATED_GAS_USED * gas_price) / 1e18
    gas_cost_usdt = gas_cost_eth * price_dex

    final_usdt = gross_revenue_usdt - uniswap_fee
    net_profit = final_usdt - investment - gas_cost_usdt
    return net_profit


def calculate_profit_buy_dex_sell_cex(investment, price_dex, price_cex, gas_price):
    # --- BUG 修复：添加缺失的变量定义 ---
    gas_cost_eth = (ESTIMATED_GAS_USED * gas_price) / 1e18
    gas_cost_usdt = gas_cost_eth * price_dex

    total_investment = investment + gas_cost_usdt
    uniswap_fee = investment * UNISWAP_FEE_RATE
    # --- 修复结束 ---

    eth_acquired = (investment - uniswap_fee) / price_dex
    gross_revenue_usdt = eth_acquired * price_cex
    binance_fee = gross_revenue_usdt * BINANCE_FEE_RATE

    final_usdt = gross_revenue_usdt - binance_fee
    net_profit = final_usdt - total_investment
    return net_profit


def analyze_opportunities(price_pairs: list):
    """
    修改后的函数：不再执行任何数据库查询。
    它只遍历服务器返回的配对列表，并进行纯 Python 计算。
    """
    logger.info("开始在本地内存中分析套利机会...")
    profitable_trades = []

    for row in price_pairs:
        # 从行中解包数据
        # (我们不需要 block_time，但保留它以便调试)
        # block_time = row[0]
        uniswap_price = pd.to_numeric(row[1], errors="coerce")
        gas_price = pd.to_numeric(row[2], errors="coerce")
        binance_price = pd.to_numeric(row[3], errors="coerce")

        # 检查数据是否有效
        if pd.isna(uniswap_price) or pd.isna(gas_price) or pd.isna(binance_price):
            continue

        # 方向1: 币安买, Uniswap卖
        # 条件: Uniswap价格 > 币安价格
        if uniswap_price > binance_price:
            # --- 添加新检查 ---
            # 如果 binance_price (即 price_cex) 为 0，则无法计算，跳过
            if binance_price == 0:
                continue
            # --- 检查结束 ---

            profit = calculate_profit_buy_cex_sell_dex(
                INITIAL_INVESTMENT_USDT, binance_price, uniswap_price, gas_price
            )
            if profit > PROFIT_THRESHOLD_USDT:
                logger.info(f"发现机会! 利润: ${profit:.2f} USDT")
                profitable_trades.append(
                    {
                        "buy_platform": "Binance",
                        "sell_platform": "Uniswap",
                        "buy_price": binance_price,
                        "sell_price": uniswap_price,
                        "profit_usdt": profit,
                    }
                )

        # 方向2: Uniswap买, 幣安卖
        # 条件: 币安价格 > Uniswap价格
        elif binance_price > uniswap_price:
            # --- 添加新检查 ---
            # 如果 uniswap_price (即 price_dex) 为 0，则无法计算，跳过
            if uniswap_price == 0:
                continue
            # --- 检查结束 ---

            profit = calculate_profit_buy_dex_sell_cex(
                INITIAL_INVESTMENT_USDT, uniswap_price, binance_price, gas_price
            )
            if profit > PROFIT_THRESHOLD_USDT:
                logger.info(f"发现机会! 利润: ${profit:.2f} USDT")
                profitable_trades.append(
                    {
                        "buy_platform": "Uniswap",
                        "sell_platform": "Binance",
                        "buy_price": uniswap_price,
                        "sell_price": binance_price,
                        "profit_usdt": profit,
                    }
                )

    return profitable_trades


def save_results(results):
    if not results:
        logger.info("未发现任何符合条件的套利机会。")
        return

    logger.info(f"分析完成，共发现 {len(results)} 条套利机会。正在存入数据库...")
    results_df = pd.DataFrame(results)
    try:
        logger.info("正在重建 arbitrage_opportunities 表...")
        cur.execute("DROP TABLE IF EXISTS arbitrage_opportunities;")
        cur.execute(
            """
            CREATE TABLE arbitrage_opportunities (
                buy_platform text,
                sell_platform text,
                buy_price numeric,
                sell_price numeric,
                profit_usdt numeric
            );
            """
        )

        if not results_df.empty:
            records = results_df[
                [
                    "buy_platform",
                    "sell_platform",
                    "buy_price",
                    "sell_price",
                    "profit_usdt",
                ]
            ].values.tolist()
            execute_values(
                cur,
                "INSERT INTO arbitrage_opportunities (buy_platform, sell_platform, buy_price, sell_price, profit_usdt) VALUES %s",
                records,
            )
        conn.commit()
        logger.info("结果已成功存入 arbitrage_opportunities 表并提交！")
    except Exception as e:
        conn.rollback()
        logger.error(f"写入结果失败，已回滚。错误: {e}")


if __name__ == "__main__":
    start_ts, end_ts = parse_cli_args()

    # 1. 替换 load_data 为 fetch_price_pairs
    # 这一步现在是唯一的数据库查询
    price_pairs_list = fetch_price_pairs(start_ts, end_ts)

    # 2. 执行分析 (现在在纯 Python 内存中进行)
    opportunities = analyze_opportunities(price_pairs_list)

    # 3. 保存结果
    save_results(opportunities)

    # 4. 清理连接
    try:
        cur.close()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass
