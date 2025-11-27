import argparse
from typing import Any, Optional, Tuple

import pandas as pd
import psycopg2
import yaml
from loguru import logger
from psycopg2.extras import Json, execute_values
from .task_client import TaskClient, load_config_from_string

# 默认策略参数
DEFAULT_STRATEGY = {
    "binance_fee_rate": 0.001,
    "uniswap_fee_rate": 0.0005,
    "estimated_gas_used": 20,
    "initial_investment": 100000.0,
    "time_delay_seconds": 3,
    "window_seconds": 5,
    "profit_threshold": 10,
}

with open("config/config.yaml", "r", encoding="utf-8") as file:
    _CONFIG = yaml.safe_load(file)

DEFAULT_DB_CONFIG = _CONFIG.get("db", {})


def _build_db_conn(overrides: dict[str, Any]):
    cfg = DEFAULT_DB_CONFIG.copy()
    cfg.update(overrides or {})
    conn = psycopg2.connect(
        host=cfg.get("host"),
        port=cfg.get("port"),
        dbname=cfg.get("database"),
        user=cfg.get("username"),
        password=cfg.get("password"),
    )
    conn.autocommit = False
    return conn


def _parse_timestamp(value: Optional[str]) -> Optional[pd.Timestamp]:
    if not value:
        return None
    return pd.to_datetime(value, utc=True, errors="raise")


def fetch_price_pairs(
    conn,
    strategy: dict[str, Any],
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
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
    logger.info("计算完成，从服务器收到 %s 对价格。", len(price_pairs))
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
    logger.info("分析结束，本次找到 %s 条机会", len(profitable_trades))
    return profitable_trades


def save_results(
    conn,
    results: list[dict[str, Any]],
    batch_id: int,
    append: bool,
    rebuild_table: bool = False,
    experiment_id: Optional[int] = None,
) -> None:
    with conn.cursor() as cur:
        if rebuild_table:
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
        elif not append:
            logger.info("清理批次 %s 旧数据", batch_id)
            cur.execute(
                "DELETE FROM arbitrage_opportunities WHERE batch_id = %s", (batch_id,)
            )

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


def run_analyse(task_id: Optional[str] = None, config_json: Optional[str] = None):
    config = load_config_from_string(config_json)
    client = TaskClient(task_id)
    strategy = DEFAULT_STRATEGY.copy()
    strategy.update(config.get("strategy", {}))
    batch_id = int(config.get("batch_id", 1))
    append = bool(config.get("append", False))
    rebuild_table = bool(config.get("rebuild_table", False))
    experiment_id = config.get("experiment_id")

    start_ts = _parse_timestamp(config.get("start"))
    end_ts = _parse_timestamp(config.get("end"))
    if start_ts and end_ts and start_ts > end_ts:
        raise ValueError("start 必须早于 end")

    client.update_status("running", "套利分析任务启动")
    conn = _build_db_conn(config.get("db", {}))
    try:
        price_pairs = fetch_price_pairs(conn, strategy, start_ts, end_ts)
        opportunities = analyze_opportunities(price_pairs, strategy)
        save_results(
            conn, opportunities, batch_id, append, rebuild_table, experiment_id
        )
    except Exception as exc:
        conn.rollback()
        client.update_status("failed", f"分析失败: {exc}")
        conn.close()
        raise
    else:
        client.update_status("success", f"分析完成，发现 {len(opportunities)} 条机会")
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="套利分析任务")
    parser.add_argument("--task-id", dest="task_id", default=None)
    parser.add_argument("--config", dest="config", default=None, help="JSON 配置")
    args = parser.parse_args()
    run_analyse(args.task_id, args.config)


if __name__ == "__main__":
    main()
