import argparse
import datetime
import time
from typing import Any, Optional

import pandas as pd
import psycopg2
import yaml
from loguru import logger
from psycopg2.extras import execute_values
from tqdm import tqdm

from task_client import TaskClient, load_config_from_string

with open("config/config.yaml", "r", encoding="utf-8") as file:
    _CONFIG = yaml.safe_load(file)

DEFAULT_DB_CONFIG = _CONFIG.get("db", {})

SQL_TEMPLATE = """
(
    SELECT 
        date_trunc(%s, block_time) AS time_bucket,
        'Uniswap' AS source,
        AVG(price) AS average_price
    FROM 
        uniswap_swaps
    WHERE 
        block_time BETWEEN %s AND %s
    GROUP BY 
        time_bucket
)
UNION ALL
(
    SELECT 
        date_trunc(%s, trade_time) AS time_bucket,
        'Binance' AS source,
        AVG(price) AS average_price
    FROM 
        binance_trades
    WHERE 
        trade_time BETWEEN %s AND %s
    GROUP BY 
        time_bucket
);
"""


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


def _daterange(start: datetime.datetime, end: datetime.datetime):
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += datetime.timedelta(days=1)


def _parse_date(value: Optional[str], default: datetime.datetime) -> datetime.datetime:
    if not value:
        return default
    dt = datetime.datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def _write_aggregated_prices(conn, df: pd.DataFrame, overwrite: bool):
    logger.info("准备写入 %s 条聚合记录", len(df))
    with conn.cursor() as cur:
        if overwrite:
            logger.info("正在重建 aggregated_prices 表...")
            cur.execute("DROP TABLE IF EXISTS aggregated_prices;")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS aggregated_prices (
                    time_bucket timestamptz,
                    source text,
                    average_price numeric
                );
                """
            )
        records = df[["time_bucket", "source", "average_price"]].values.tolist()
        execute_values(
            cur,
            "INSERT INTO aggregated_prices (time_bucket, source, average_price) VALUES %s",
            records,
        )
    conn.commit()
    logger.info("聚合结果写入完成。")


def run_process_prices(task_id: Optional[str] = None, config_json: Optional[str] = None):
    config = load_config_from_string(config_json)
    client = TaskClient(task_id)
    aggregation_interval = config.get("aggregation_interval", "minute")
    overwrite = bool(config.get("overwrite", True))
    db_overrides = config.get("db", {})

    default_start = datetime.datetime(2025, 9, 1, tzinfo=datetime.timezone.utc)
    default_end = default_start + datetime.timedelta(days=29)
    start_dt = _parse_date(config.get("start_date"), default_start)
    end_dt = _parse_date(config.get("end_date"), default_end)
    if end_dt < start_dt:
        raise ValueError("end_date 不能早于 start_date")

    client.update_status(
        "running", f"开始聚合 {start_dt.date()} - {end_dt.date()} 数据，粒度 {aggregation_interval}"
    )

    conn = _build_db_conn(db_overrides)
    all_days_dfs = []
    num_days = (end_dt.date() - start_dt.date()).days + 1
    logger.info("正在按天聚合，共 %s 天", num_days)
    start_time = time.time()
    with conn.cursor() as cur:
        for day in tqdm(_daterange(start_dt, end_dt), desc="聚合每日数据"):
            day_start = datetime.datetime(
                day.year, day.month, day.day, 0, 0, 0, tzinfo=datetime.timezone.utc
            )
            day_end = datetime.datetime(
                day.year, day.month, day.day, 23, 59, 59, tzinfo=datetime.timezone.utc
            )
            try:
                params = (
                    aggregation_interval,
                    day_start,
                    day_end,
                    aggregation_interval,
                    day_start,
                    day_end,
                )
                cur.execute(SQL_TEMPLATE, params)
                rows = cur.fetchall()
                if rows:
                    day_df = pd.DataFrame(rows, columns=["time_bucket", "source", "average_price"])
                    all_days_dfs.append(day_df)
            except Exception as exc:
                logger.warning("处理 %s 发生错误: %s", day_start.date(), exc)

    if not all_days_dfs:
        logger.info("没有聚合出任何数据。")
        client.update_status("success", "无数据可写入")
        conn.close()
        return

    df_final = pd.concat(all_days_dfs)
    duration = time.time() - start_time
    logger.info("聚合完成，共 %s 条记录，耗时 %.2fs", len(df_final), duration)
    try:
        _write_aggregated_prices(conn, df_final, overwrite=overwrite)
    except Exception as exc:
        conn.rollback()
        client.update_status("failed", f"写入失败: {exc}")
        conn.close()
        raise
    else:
        client.update_status(
            "success",
            f"聚合完成，共写入 {len(df_final)} 条记录",
            {"rows": len(df_final), "duration": duration},
        )
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="聚合 Uniswap 与 Binance 的价格数据")
    parser.add_argument("--task-id", dest="task_id", default=None)
    parser.add_argument("--config", dest="config", default=None)
    args = parser.parse_args()
    run_process_prices(args.task_id, args.config)


if __name__ == "__main__":
    main()
