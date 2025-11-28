import argparse
from typing import Any, Optional, Tuple

import pandas as pd
import psycopg2
import yaml
from loguru import logger
from psycopg2.extras import Json, execute_values

from .task import check_task, update_task_status

with open("../config/config.yaml", "r", encoding="utf-8") as file:
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
                gas_price
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
    profitable_trades = []
    threshold = float(strategy["profit_threshold"])

    for row in price_pairs:
        block_time = row[0]
        uniswap_price = pd.to_numeric(row[1], errors="coerce")
        gas_price = pd.to_numeric(row[2], errors="coerce")
        binance_price = pd.to_numeric(row[3], errors="coerce")

        if pd.isna(uniswap_price) or pd.isna(gas_price) or pd.isna(binance_price):
            continue

        if uniswap_price > binance_price and binance_price != 0:
            profit = calculate_profit_buy_cex_sell_dex(
                strategy, binance_price, uniswap_price, gas_price
            )
            if profit > threshold:
                profitable_trades.append(
                    {
                        "block_time": block_time,
                        "buy_platform": "Binance",
                        "sell_platform": "Uniswap",
                        "buy_price": float(binance_price),
                        "sell_price": float(uniswap_price),
                        "profit_usdt": float(profit),
                    }
                )
        elif binance_price > uniswap_price and uniswap_price != 0:
            profit = calculate_profit_buy_dex_sell_cex(
                strategy, uniswap_price, binance_price, gas_price
            )
            if profit > threshold:
                profitable_trades.append(
                    {
                        "block_time": block_time,
                        "buy_platform": "Uniswap",
                        "sell_platform": "Binance",
                        "buy_price": float(uniswap_price),
                        "sell_price": float(binance_price),
                        "profit_usdt": float(profit),
                    }
                )
    logger.info(f"分析结束，本次找到 {len(profitable_trades)} 条机会")
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
                    details_json jsonb
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

        logger.info("正在写入 %s 条套利机会...", len(results))
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
                )
            )
        execute_values(
            cur,
            """
            INSERT INTO arbitrage_opportunities
            (batch_id, buy_platform, sell_platform, buy_price, sell_price, profit_usdt, details_json)
            VALUES %s
            """,
            records,
        )
    conn.commit()
    logger.info("写入完成并已提交。")


def run_analyse(
    task_id: Optional[str] = None,
    config_json: Optional[str] = None,
    **kwargs
):
    strategy_params = {
        "binance_fee_rate": kwargs.get("binance_fee_rate", 0.001),
        "uniswap_fee_rate": kwargs.get("uniswap_fee_rate", 0.0005),
        "estimated_gas_used": kwargs.get("estimated_gas_used", 20),
        "initial_investment": kwargs.get("initial_investment", 100000.0),
        "time_delay_seconds": kwargs.get("time_delay_seconds", 3),
        "window_seconds": kwargs.get("window_seconds", 5),
        "profit_threshold": kwargs.get("profit_threshold", 10),
    }
    batch_id = int(kwargs.get("batch_id", 1))
    overwrite = bool(kwargs.get("overwrite", False))
    experiment_id = kwargs.get("experiment_id")

    start_ts = _parse_timestamp(kwargs.get("start"))
    end_ts = _parse_timestamp(kwargs.get("end"))
    if start_ts and end_ts and start_ts > end_ts:
        raise ValueError("start 必须早于 end")
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
        price_pairs = fetch_price_pairs(conn, strategy_params, start_ts, end_ts)
        opportunities = analyze_opportunities(price_pairs, strategy_params)
        save_results(
            conn, opportunities, batch_id, overwrite, experiment_id
        )
    except Exception as exc:
        conn.rollback()
        logger.error(f"分析失败: {exc}")
        conn.close()
        raise
    else:
        logger.info(f"分析完成，发现 {len(opportunities)} 条机会")
        conn.close()

if __name__ == "__main__":
    run_analyse(task_id="1", config_json="", binance_fee_rate=0.001, uniswap_fee_rate=0.0005, estimated_gas_used=20, initial_investment=100000.0, time_delay_seconds=3, window_seconds=5, profit_threshold=10)