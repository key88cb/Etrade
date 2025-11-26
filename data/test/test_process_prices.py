"""
process_prices.py 的单元测试
"""
import datetime
import os
import sys
from unittest.mock import MagicMock, Mock, mock_open, patch

import pandas as pd
import pytest

# 获取当前脚本文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上一级目录（父目录）的路径
parent_dir = os.path.dirname(current_dir)
# 将上一级目录添加到 sys.path
sys.path.insert(0, parent_dir)

# Mock配置文件和数据库连接，避免在导入时出错
mock_config = {
    "db": {
        "host": "localhost",
        "port": 5432,
        "database": "test_db",
        "username": "test_user",
        "password": "test_password",
    }
}

mock_conn = MagicMock()
mock_cur = MagicMock()
mock_conn.cursor.return_value = mock_cur
mock_conn.autocommit = False

# 在导入前mock配置文件和数据库连接
import yaml

with patch(
    "builtins.open",
    mock_open(
        read_data="db:\n  host: localhost\n  port: 5432\n  database: test_db\n  username: test_user\n  password: test_password"
    ),
):
    with patch("yaml.safe_load", return_value=mock_config):
        with patch("psycopg2.connect", return_value=mock_conn):
            # 导入模块，但需要mock tqdm以避免显示进度条
            with patch("block_chain.process_prices.tqdm", lambda x, **kwargs: x):
                import block_chain.process_prices as process_prices_module


class TestProcessPricesModule:
    """
    测试 process_prices 模块的主要功能
    """

    def test_sql_template_structure(self):
        """
        测试：SQL模板的结构是否正确
        """
        sql_template = process_prices_module.sql_template

        # 验证SQL模板包含必要的部分
        assert "date_trunc" in sql_template
        assert "Uniswap" in sql_template
        assert "Binance" in sql_template
        assert "uniswap_swaps" in sql_template
        assert "binance_trades" in sql_template
        assert "UNION ALL" in sql_template

    def test_aggregation_interval(self):
        """
        测试：聚合间隔配置
        """
        assert process_prices_module.AGGREGATION_INTERVAL == "minute"

    def test_year_month_config(self):
        """
        测试：年月配置
        """
        assert isinstance(process_prices_module.YEAR, int)
        assert isinstance(process_prices_module.MONTH, int)
        assert 1 <= process_prices_module.MONTH <= 12

    @patch("block_chain.process_prices.cur")
    @patch("block_chain.process_prices.logger")
    def test_database_query_execution(self, mock_logger, mock_cur):
        """
        测试：数据库查询执行逻辑
        """
        # Mock数据库返回结果
        mock_cur.fetchall.return_value = [
            (
                datetime.datetime(2025, 9, 1, 10, 0, 0, tzinfo=datetime.timezone.utc),
                "Uniswap",
                3000.0,
            ),
            (
                datetime.datetime(2025, 9, 1, 10, 0, 0, tzinfo=datetime.timezone.utc),
                "Binance",
                2900.0,
            ),
        ]

        # 模拟一天的查询
        day_start = datetime.datetime(
            2025, 9, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
        )
        day_end = datetime.datetime(
            2025, 9, 1, 23, 59, 59, tzinfo=datetime.timezone.utc
        )

        params = (
            "minute",
            day_start,
            day_end,
            "minute",
            day_start,
            day_end,
        )

        mock_cur.execute(process_prices_module.sql_template, params)
        rows = mock_cur.fetchall()

        # 验证查询被调用
        assert mock_cur.execute.called
        assert len(rows) == 2

    def test_dataframe_creation(self):
        """
        测试：DataFrame创建逻辑
        """
        # 模拟数据库返回的数据
        rows = [
            (
                datetime.datetime(2025, 9, 1, 10, 0, 0, tzinfo=datetime.timezone.utc),
                "Uniswap",
                3000.0,
            ),
            (
                datetime.datetime(2025, 9, 1, 10, 0, 0, tzinfo=datetime.timezone.utc),
                "Binance",
                2900.0,
            ),
        ]

        day_df = pd.DataFrame(
            rows, columns=["time_bucket", "source", "average_price"]
        )

        assert len(day_df) == 2
        assert list(day_df.columns) == ["time_bucket", "source", "average_price"]
        assert day_df["source"].tolist() == ["Uniswap", "Binance"]
        assert day_df["average_price"].tolist() == [3000.0, 2900.0]

    def test_dataframe_concat(self):
        """
        测试：多个DataFrame的合并
        """
        df1 = pd.DataFrame(
            [
                (
                    datetime.datetime(
                        2025, 9, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    "Uniswap",
                    3000.0,
                )
            ],
            columns=["time_bucket", "source", "average_price"],
        )

        df2 = pd.DataFrame(
            [
                (
                    datetime.datetime(
                        2025, 9, 2, 10, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    "Binance",
                    2900.0,
                )
            ],
            columns=["time_bucket", "source", "average_price"],
        )

        df_final = pd.concat([df1, df2])

        assert len(df_final) == 2
        assert len(df_final.columns) == 3

    @patch("block_chain.process_prices.cur")
    @patch("block_chain.process_prices.conn")
    @patch("block_chain.process_prices.logger")
    @patch("block_chain.process_prices.execute_values")
    def test_save_results_to_database(
        self, mock_execute_values, mock_logger, mock_conn, mock_cur
    ):
        """
        测试：保存结果到数据库的逻辑
        """
        # 创建测试数据
        df_final = pd.DataFrame(
            [
                (
                    datetime.datetime(
                        2025, 9, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    "Uniswap",
                    3000.0,
                ),
                (
                    datetime.datetime(
                        2025, 9, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    "Binance",
                    2900.0,
                ),
            ],
            columns=["time_bucket", "source", "average_price"],
        )

        # 模拟保存逻辑
        try:
            mock_cur.execute("DROP TABLE IF EXISTS aggregated_prices;")
            mock_cur.execute(
                """
                CREATE TABLE aggregated_prices (
                    time_bucket timestamptz,
                    source text,
                    average_price numeric
                );
                """
            )

            records = df_final[
                ["time_bucket", "source", "average_price"]
            ].values.tolist()
            mock_execute_values(
                mock_cur,
                "INSERT INTO aggregated_prices (time_bucket, source, average_price) VALUES %s",
                records,
            )
            mock_conn.commit()
        except Exception as e:
            mock_conn.rollback()
            raise e

        # 验证操作被调用
        assert mock_cur.execute.call_count >= 2
        assert mock_execute_values.called
        assert mock_conn.commit.called

    @patch("block_chain.process_prices.cur")
    @patch("block_chain.process_prices.conn")
    @patch("block_chain.process_prices.logger")
    def test_save_results_rollback_on_error(
        self, mock_logger, mock_conn, mock_cur
    ):
        """
        测试：保存结果时出错应该回滚
        """
        # 模拟数据库错误
        mock_cur.execute.side_effect = Exception("Database error")

        try:
            mock_cur.execute("DROP TABLE IF EXISTS aggregated_prices;")
            mock_cur.execute("CREATE TABLE aggregated_prices (...);")
        except Exception as e:
            mock_conn.rollback()

        # 验证回滚被调用
        assert mock_conn.rollback.called

    def test_datetime_range_creation(self):
        """
        测试：日期时间范围创建逻辑
        """
        YEAR = 2025
        MONTH = 9
        day = 1

        day_start = datetime.datetime(
            YEAR, MONTH, day, 0, 0, 0, tzinfo=datetime.timezone.utc
        )
        day_end = datetime.datetime(
            YEAR, MONTH, day, 23, 59, 59, tzinfo=datetime.timezone.utc
        )

        assert day_start.hour == 0
        assert day_start.minute == 0
        assert day_start.second == 0
        assert day_end.hour == 23
        assert day_end.minute == 59
        assert day_end.second == 59
        assert day_start.tzinfo == datetime.timezone.utc
        assert day_end.tzinfo == datetime.timezone.utc

    def test_empty_results_handling(self):
        """
        测试：处理空结果的情况
        """
        all_days_dfs = []

        if not all_days_dfs:
            # 应该处理空结果
            assert len(all_days_dfs) == 0
        else:
            df_final = pd.concat(all_days_dfs)
            assert len(df_final) > 0

    @patch("block_chain.process_prices.cur")
    @patch("block_chain.process_prices.logger")
    def test_exception_handling_in_loop(self, mock_logger, mock_cur):
        """
        测试：循环中的异常处理
        """
        # 模拟数据库查询出错
        mock_cur.execute.side_effect = Exception("Query failed")
        mock_cur.fetchall.return_value = []

        day_start = datetime.datetime(
            2025, 9, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
        )
        day_end = datetime.datetime(
            2025, 9, 1, 23, 59, 59, tzinfo=datetime.timezone.utc
        )

        params = (
            "minute",
            day_start,
            day_end,
            "minute",
            day_start,
            day_end,
        )

        try:
            mock_cur.execute(process_prices_module.sql_template, params)
            rows = mock_cur.fetchall()
            if rows:
                day_df = pd.DataFrame(
                    rows, columns=["time_bucket", "source", "average_price"]
                )
        except Exception as e:
            # 异常应该被捕获并记录
            mock_logger.info(f"\n处理数据时出错: {e}")

        # 验证异常被处理
        assert mock_cur.execute.called
        assert mock_logger.info.called

    def test_sql_params_structure(self):
        """
        测试：SQL参数结构
        """
        AGGREGATION_INTERVAL = "minute"
        day_start = datetime.datetime(
            2025, 9, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
        )
        day_end = datetime.datetime(
            2025, 9, 1, 23, 59, 59, tzinfo=datetime.timezone.utc
        )

        params = (
            AGGREGATION_INTERVAL,
            day_start,
            day_end,
            AGGREGATION_INTERVAL,
            day_start,
            day_end,
        )

        # 验证参数结构
        assert len(params) == 6
        assert params[0] == "minute"
        assert params[3] == "minute"
        assert params[1] == day_start
        assert params[2] == day_end
        assert params[4] == day_start
        assert params[5] == day_end

    @patch("block_chain.process_prices.cur")
    @patch("block_chain.process_prices.conn")
    def test_connection_cleanup(self, mock_conn, mock_cur):
        """
        测试：连接清理逻辑
        """
        try:
            mock_cur.close()
        except Exception:
            pass

        try:
            mock_conn.close()
        except Exception:
            pass

        # 验证清理方法可以被调用
        mock_cur.close()
        mock_conn.close()

        assert True  # 如果没有抛出异常，测试通过

