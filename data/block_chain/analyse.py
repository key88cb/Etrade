import argparse
from typing import Any, Optional, Tuple

import pandas as pd
import psycopg2
import yaml
from loguru import logger
from psycopg2.extras import Json, execute_values

from .task import check_task, update_task_status
from .utils import load_config_from_string

DEFAULT_STRATEGY = {
    "binance_fee_rate": 0.001,
    "uniswap_fee_rate": 0.0005,
    "estimated_gas_used": 20,
    "initial_investment": 1000.0,
    "time_delay_seconds": 3,
    "window_seconds": 5,
    "profit_threshold": 1,
}

with open("./config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

db_config = config.get("db", {})

def _parse_timestamp(value: str) -> pd.Timestamp:
    if not value:
        return None
    return pd.to_datetime(value, utc=True, errors="raise")

def fetch_price_pairs(
    conn,
    strategy: dict[str, Any],
    start_time: pd.Timestamp = None,
    end_time: pd.Timestamp = None,
) -> list[Tuple]:
    """
    使用单个 SQL JOIN 查询，让数据库服务器完成所有繁重的计算.
    """
    logger.info("正在请求服务器计算并返回所有价格对...")
    params = {
        "delay_seconds": f"{strategy['time_delay_seconds']} seconds",
        "window_seconds": f"{strategy['window_seconds']} seconds",
    }
    time_conditions = []
    if start_time is not None:
        params["start_ts"] = start_time.to_pydatetime()
        time_conditions.append("u.block_time >= %(start_ts)s")
    if end_time is not None:
        params["end_ts"] = end_time.to_pydatetime()
        time_conditions.append("u.block_time <= %(end_ts)s")
    where_clause = f"WHERE {' AND '.join(time_conditions)}" if time_conditions else ""

    sql_query = f"""
        WITH 
        config AS (
            SELECT 
                %(delay_seconds)s::interval AS delay,
                %(window_seconds)s::interval AS window
        ),
        uniswap_data AS (
            SELECT 
                block_time, 
                price AS uniswap_price, 
                gas_price,
                -- 计算过去 10 分钟的绝对累计成交量 (ETH) 作为市场深度/流动性的代理
                SUM(ABS(amount_eth)) OVER (
                    ORDER BY block_time 
                    RANGE BETWEEN INTERVAL '10 minutes' PRECEDING AND CURRENT ROW
                ) as window_volume
            FROM uniswap_swaps u
            {where_clause}
        ),
        binance_avg AS (
            SELECT 
                u.block_time,
                AVG(b.price) AS binance_price
            FROM 
                uniswap_data u
            CROSS JOIN 
                config c 
            JOIN 
                binance_trades b 
            ON 
                b.trade_time BETWEEN 
                    (u.block_time - c.delay - c.window)
                AND 
                    (u.block_time - c.delay + c.window)
            GROUP BY 
                u.block_time
        )
        SELECT 
            u.block_time,
            u.uniswap_price,
            u.gas_price,
            u.window_volume,
            b.binance_price
        FROM 
            uniswap_data u
        JOIN 
            binance_avg b ON u.block_time = b.block_time
        ORDER BY
            u.block_time;
    """
    with conn.cursor() as cur:
        cur.execute(sql_query, params)
        price_pairs = cur.fetchall()
    logger.info(f"计算完成，从服务器收到 {len(price_pairs)} 对价格。")
    return price_pairs


def calculate_profit_buy_cex_sell_dex(
    strategy: dict[str, Any], price_cex, price_dex, gas_price
):
    investment = strategy["initial_investment"]
    binance_fee = strategy["binance_fee_rate"]
    uniswap_fee = strategy["uniswap_fee_rate"]
    gas_used = strategy["estimated_gas_used"]

    eth_acquired = (investment * (1 - binance_fee)) / price_cex
    gross_revenue_usdt = eth_acquired * price_dex
    uniswap_fee_value = gross_revenue_usdt * uniswap_fee

    gas_cost_eth = (gas_used * gas_price) / 1e18
    gas_cost_usdt = gas_cost_eth * price_dex

    final_usdt = gross_revenue_usdt - uniswap_fee_value
    net_profit = final_usdt - investment - gas_cost_usdt
    return net_profit


def calculate_profit_buy_dex_sell_cex(
    strategy: dict[str, Any], price_dex, price_cex, gas_price
):
    investment = strategy["initial_investment"]
    binance_fee = strategy["binance_fee_rate"]
    uniswap_fee = strategy["uniswap_fee_rate"]
    gas_used = strategy["estimated_gas_used"]

    gas_cost_eth = (gas_used * gas_price) / 1e18
    gas_cost_usdt = gas_cost_eth * price_dex
    total_investment = investment + gas_cost_usdt
    uniswap_fee_value = investment * uniswap_fee

    eth_acquired = (investment - uniswap_fee_value) / price_dex
    gross_revenue_usdt = eth_acquired * price_cex
    binance_fee_value = gross_revenue_usdt * binance_fee

    final_usdt = gross_revenue_usdt - binance_fee_value
    net_profit = final_usdt - total_investment
    return net_profit


def analyze_opportunities(price_pairs: list, strategy: dict[str, Any]):
    logger.info("开始在本地内存中分析套利机会...")
    from .analyze_risk import calculate_risk_metrics_local

    profitable_trades = []
    threshold = float(strategy["profit_threshold"])
    investment = float(strategy["initial_investment"])

    # 将 price_pairs 转为 DataFrame 以便计算波动率
    # 注意：现在多了 window_volume 列
    df = pd.DataFrame(price_pairs, columns=["block_time", "uniswap_price", "gas_price", "window_volume", "binance_price"])
    # 确保类型正确
    df["uniswap_price"] = pd.to_numeric(df["uniswap_price"], errors="coerce")
    df["binance_price"] = pd.to_numeric(df["binance_price"], errors="coerce")
    df["window_volume"] = pd.to_numeric(df["window_volume"], errors="coerce").fillna(0)
    
    # 计算滑动窗口波动率 (Rolling Volatility)
    # 假设数据是按时间排序的。计算过去 10 个点的标准差作为波动率估计
    df["volatility"] = df["uniswap_price"].rolling(window=10).std() / df["uniswap_price"].rolling(window=10).mean()
    df["volatility"] = df["volatility"].fillna(0)

    for index, row in df.iterrows():
        block_time = row["block_time"]
        uniswap_price = row["uniswap_price"]
        gas_price = row["gas_price"]
        binance_price = row["binance_price"]
        volatility = row["volatility"]
        # 使用数据库查出来的真实 volume
        market_volume = row["window_volume"]

        if pd.isna(uniswap_price) or pd.isna(gas_price) or pd.isna(binance_price):
            continue

        opp = None
        if uniswap_price > binance_price and binance_price != 0:
            profit = calculate_profit_buy_cex_sell_dex(
                strategy, binance_price, uniswap_price, gas_price
            )
            if profit > threshold:
                opp = {
                    "block_time": block_time,
                    "buy_platform": "Binance",
                    "sell_platform": "Uniswap",
                    "buy_price": float(binance_price),
                    "sell_price": float(uniswap_price),
                    "profit_usdt": float(profit),
                }
        elif binance_price > uniswap_price and uniswap_price != 0:
            profit = calculate_profit_buy_dex_sell_cex(
                strategy, uniswap_price, binance_price, gas_price
            )
            if profit > threshold:
                opp = {
                    "block_time": block_time,
                    "buy_platform": "Uniswap",
                    "sell_platform": "Binance",
                    "buy_price": float(uniswap_price),
                    "sell_price": float(binance_price),
                    "profit_usdt": float(profit),
                }
        
        if opp:
            # 集成风险分析
            risk_metrics = calculate_risk_metrics_local(
                opp, volatility, market_volume, investment
            )
            opp["risk_metrics"] = risk_metrics
            profitable_trades.append(opp)

    logger.info("分析结束，本次找到 %s 条机会", len(profitable_trades))
    return profitable_trades


def save_results(
    conn,
    results: list[dict[str, Any]],
    batch_id: int,
    overwrite: bool = False,
    experiment_id: Optional[int] = None,
) -> None:
    with conn.cursor() as cur:
        if overwrite:
            logger.info("正在重建 arbitrage_opportunities 表...")
            cur.execute("DROP TABLE IF EXISTS arbitrage_opportunities;")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                    id SERIAL PRIMARY KEY,
                    batch_id integer,
                    buy_platform text,
                    sell_platform text,
                    buy_price numeric,
                    sell_price numeric,
                    profit_usdt numeric,
                    details_json jsonb,
                    risk_metrics_json jsonb
                );
                """
            )
        else:
            # overwrite=False 时追加数据，不删除旧数据
            pass

        if not results:
            conn.commit()
            logger.info("没有结果需要写入。")
            return

        logger.info(f"正在写入 {len(results)} 条套利机会...")
        records = []
        for item in results:
            details = {
                "block_time": (
                    item["block_time"].isoformat() if item.get("block_time") else None
                ),
                "experiment_id": experiment_id,
            }
            records.append(
                (
                    batch_id,
                    item["buy_platform"],
                    item["sell_platform"],
                    item["buy_price"],
                    item["sell_price"],
                    item["profit_usdt"],
                    Json(details),
                    # 独立存入 risk_metrics_json
                    Json(item.get("risk_metrics", {}))
                )
            )
        execute_values(
            cur,
            """
            INSERT INTO arbitrage_opportunities
            (batch_id, buy_platform, sell_platform, buy_price, sell_price, profit_usdt, details_json, risk_metrics_json)
            VALUES %s
            """,
            records,
    )
    conn.commit()
    logger.info("写入完成并已提交。")


def ensure_batch_exists(conn, batch_id: int) -> None:
    if not batch_id:
        return
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM batches WHERE id = %s", (batch_id,))
        if cur.fetchone():
            return
        name = f"Auto Batch {batch_id}"
        description = "批次由套利分析脚本自动创建"
        logger.info("批次 %s 不存在，自动创建", batch_id)
        cur.execute(
            """
            INSERT INTO batches (id, name, description, last_refreshed_at, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW(), NOW())
            """,
            (batch_id, name, description),
        )
    conn.commit()


def run_analyse(task_id: Optional[str] = None, config_json: Optional[str] = None):
    config = load_config_from_string(config_json)
    # 默认策略 + 自定义参数
    strategy = DEFAULT_STRATEGY.copy()
    strategy.update(config.get("strategy", {}))
    batch_id = int(config.get("batch_id", 1))
    overwrite = bool(config.get("overwrite", False))
    experiment_id = config.get("experiment_id")

    start_ts = _parse_timestamp(strategy.get("start"))
    end_ts = _parse_timestamp(strategy.get("end"))
    if start_ts and end_ts and start_ts > end_ts:
        update_task_status(task_id, 2)
        return

    logger.info("套利分析任务启动")
    conn = psycopg2.connect(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["database"],
        user=db_config["username"],
        password=db_config["password"],
    )
    conn.autocommit = False
    try:
        ensure_batch_exists(conn, batch_id)
        price_pairs = fetch_price_pairs(conn, strategy, start_ts, end_ts)
        opportunities = analyze_opportunities(price_pairs, strategy)
        save_results(conn, opportunities, batch_id, overwrite, experiment_id)
    except Exception as exc:
        conn.rollback()
        logger.error(f"分析失败: {exc}")
        conn.close()
        update_task_status(task_id, 2)
        raise
    else:
        logger.info(f"分析完成，发现 {len(opportunities)} 条机会")
        update_task_status(task_id, 1)
        conn.close()


if __name__ == "__main__":
    pass