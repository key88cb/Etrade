import argparse
import datetime
import time
from typing import Any, Optional

import pandas as pd
import psycopg2
import yaml
from loguru import logger
from psycopg2.extras import execute_values

from .task import check_task, update_task_status

with open("./config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

DEFAULT_DB_CONFIG = config.get("db", {})

# 解析时间间隔
interval_map = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

# 使用数学取整法进行任意时间间隔分桶
# 这种写法兼容性好，支持 5m, 15m 等非标准 date_trunc 粒度
sql_query = """
(
    SELECT 
        to_timestamp(floor(extract(epoch from block_time) / %s) * %s) AS time_bucket,
        'Uniswap' AS source,
        AVG(price) AS average_price
    FROM 
        uniswap_swaps
    WHERE 
        block_time BETWEEN %s AND %s
    GROUP BY 
        1
)
UNION ALL
(
    SELECT 
        to_timestamp(floor(extract(epoch from trade_time) / %s) * %s) AS time_bucket,
        'Binance' AS source,
        AVG(price) AS average_price
    FROM 
        binance_trades
    WHERE 
        trade_time BETWEEN %s AND %s
    GROUP BY 
        1
);
"""


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
    logger.info(f"准备写入 {len(df)} 条聚合记录")
    with conn.cursor() as cur:
        if overwrite:
            logger.info("正在重建 aggregated_prices 表...")
            cur.execute("DROP TABLE IF EXISTS aggregated_prices")
            cur.execute(
                "CREATE TABLE IF NOT EXISTS aggregated_prices (time_bucket timestamptz, source text, average_price numeric)"
            )
        records = df[["time_bucket", "source", "average_price"]].values.tolist()
        execute_values(
            cur,
            "INSERT INTO aggregated_prices (time_bucket, source, average_price) VALUES %s",
            records,
            page_size=10000,
        )
    conn.commit()
    logger.info(f"聚合结果写入完成，写入 {len(records)} 条记录")


def run_process_prices(task_id: str, **kwargs: Any):
    aggregation_interval = kwargs.get("aggregation_interval", "minute")
    # 默认使用 1 分钟 (60秒)
    interval_seconds = interval_map.get(aggregation_interval, 60)
    overwrite = bool(kwargs.get("overwrite", True))
    start_dt = _parse_date(
        kwargs.get("start_date"),
        datetime.datetime(2025, 9, 1, tzinfo=datetime.timezone.utc),
    )
    end_dt = _parse_date(kwargs.get("end_date"), start_dt + datetime.timedelta(days=7))
    if end_dt < start_dt:
        update_task_status(task_id, 2)
        logger.error(f"end_date 不能早于 start_date")
        return
    logger.info(f"开始聚合 {start_dt} - {end_dt} 数据，粒度 {aggregation_interval}")

    conn = psycopg2.connect(
        host=DEFAULT_DB_CONFIG["host"],
        port=DEFAULT_DB_CONFIG["port"],
        dbname=DEFAULT_DB_CONFIG["database"],
        user=DEFAULT_DB_CONFIG["username"],
        password=DEFAULT_DB_CONFIG["password"],
    )
    all_days_dfs = []
    num_days = (end_dt.date() - start_dt.date()).days + 1
    logger.info(f"正在按天聚合，共 {num_days} 天")
    start_time = time.time()
    with conn.cursor() as cur:
        for day in _daterange(start_dt, end_dt):
            if check_task(task_id):
                logger.info(f"任务 {task_id} 已取消，停止聚合")
                conn.close()
                return
            day_start = datetime.datetime(
                day.year, day.month, day.day, 0, 0, 0, tzinfo=datetime.timezone.utc
            )
            day_end = datetime.datetime(
                day.year, day.month, day.day, 23, 59, 59, tzinfo=datetime.timezone.utc
            )
            try:
                params = (
                    interval_seconds,
                    interval_seconds,
                    day_start,
                    day_end,
                    interval_seconds,
                    interval_seconds,
                    day_start,
                    day_end,
                )
                cur.execute(sql_query, params)
                rows = cur.fetchall()
                if rows:
                    day_df = pd.DataFrame(
                        rows, columns=["time_bucket", "source", "average_price"]
                    )
                    all_days_dfs.append(day_df)
            except Exception as exc:
                update_task_status(task_id, 2)
                logger.warning(f"处理 {day_start.date()} 发生错误: {exc}")
                raise

    if not all_days_dfs:
        logger.info("没有聚合出任何数据。")
        conn.close()
        return

    df_final = pd.concat(all_days_dfs)
    duration = time.time() - start_time
    logger.info(f"聚合完成，共 {len(df_final)} 条记录，耗时 {duration:.2f}s")
    try:
        _write_aggregated_prices(conn, df_final, overwrite=overwrite)
    except Exception as exc:
        conn.rollback()
        logger.error(f"写入失败: {exc}")
        update_task_status(task_id, 2)
        raise
    else:
        # 在标记成功前，再次检查任务是否被取消
        if check_task(task_id):
            logger.info(f"任务 {task_id} 已取消，不标记为成功")
        else:
            logger.info(f"聚合完成，共写入 {len(df_final)} 条记录，耗时 {duration:.2f}s")
            update_task_status(task_id, 1)
    finally:
        conn.close()


if __name__ == "__main__":
    run_process_prices(
        task_id="1",
        aggregation_interval="minute",
        overwrite=True,
        start_date="2025-09-01",
        end_date="2025-09-07",
    )
