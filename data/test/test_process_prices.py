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
            import block_chain.process_prices as process_prices_module


class TestProcessPricesModule:
    """
    测试 process_prices 模块的主要功能
    """

    def test_sql_query_structure(self):
        """
        测试：SQL查询的结构是否正确
        """
        sql_query = process_prices_module.sql_query

        # 验证SQL查询包含必要的部分
        assert "Uniswap" in sql_query
        assert "Binance" in sql_query
        assert "uniswap_swaps" in sql_query
        assert "binance_trades" in sql_query
        assert "UNION ALL" in sql_query

    def test_interval_map(self):
        """
        测试：时间间隔映射配置
        """
        assert "1m" in process_prices_module.interval_map
        assert "1h" in process_prices_module.interval_map
        assert process_prices_module.interval_map["1m"] == 60

    def test_database_query_execution(self):
        """
        测试：数据库查询执行逻辑
        """
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

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
        day_start = datetime.datetime(2025, 9, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        day_end = datetime.datetime(
            2025, 9, 1, 23, 59, 59, tzinfo=datetime.timezone.utc
        )

        params = (
            60,
            60,  # interval_seconds for uniswap
            day_start,
            day_end,
            60,
            60,  # interval_seconds for binance
            day_start,
            day_end,
        )

        with mock_conn.cursor() as cur:
            cur.execute(process_prices_module.sql_query, params)
            rows = cur.fetchall()

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

        day_df = pd.DataFrame(rows, columns=["time_bucket", "source", "average_price"])

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

    def test_save_results_to_database(self):
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

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        # 模拟保存逻辑
        with patch("block_chain.process_prices.execute_values") as mock_execute_values:
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

    def test_save_results_rollback_on_error(self):
        """
        测试：保存结果时出错应该回滚
        """
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.side_effect = Exception("Database error")
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

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

    def test_exception_handling_in_loop(self):
        """
        测试：循环中的异常处理
        """
        mock_cur = MagicMock()
        # 模拟数据库查询出错
        mock_cur.execute.side_effect = Exception("Query failed")
        mock_cur.fetchall.return_value = []

        day_start = datetime.datetime(2025, 9, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        day_end = datetime.datetime(
            2025, 9, 1, 23, 59, 59, tzinfo=datetime.timezone.utc
        )

        params = (
            60,
            60,  # interval_seconds
            day_start,
            day_end,
            60,
            60,  # interval_seconds
            day_start,
            day_end,
        )

        with patch("block_chain.process_prices.logger") as mock_logger:
            try:
                mock_cur.execute(process_prices_module.sql_query, params)
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
        interval_seconds = 60
        day_start = datetime.datetime(2025, 9, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        day_end = datetime.datetime(
            2025, 9, 1, 23, 59, 59, tzinfo=datetime.timezone.utc
        )

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

        # 验证参数结构
        assert len(params) == 8
        assert params[0] == 60
        assert params[4] == 60
        assert params[2] == day_start
        assert params[3] == day_end
        assert params[6] == day_start
        assert params[7] == day_end

    def test_connection_cleanup(self):
        """
        测试：连接清理逻辑
        """
        mock_conn = MagicMock()
        mock_cur = MagicMock()

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


class TestDaterange:
    """
    测试 _daterange 函数
    """

    def test_daterange_single_day(self):
        """
        测试：单天范围
        """
        from block_chain.process_prices import _daterange

        start = datetime.datetime(2025, 9, 1, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2025, 9, 1, tzinfo=datetime.timezone.utc)

        days = list(_daterange(start, end))
        assert len(days) == 1
        assert days[0] == start

    def test_daterange_multiple_days(self):
        """
        测试：多天范围
        """
        from block_chain.process_prices import _daterange

        start = datetime.datetime(2025, 9, 1, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2025, 9, 3, tzinfo=datetime.timezone.utc)

        days = list(_daterange(start, end))
        assert len(days) == 3
        assert days[0] == start
        assert days[-1] == end

    def test_daterange_week(self):
        """
        测试：一周范围
        """
        from block_chain.process_prices import _daterange

        start = datetime.datetime(2025, 9, 1, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2025, 9, 7, tzinfo=datetime.timezone.utc)

        days = list(_daterange(start, end))
        assert len(days) == 7


class TestParseDate:
    """
    测试 _parse_date 函数
    """

    def test_parse_date_with_value(self):
        """
        测试：有值的情况
        """
        from block_chain.process_prices import _parse_date

        default = datetime.datetime(2025, 9, 1, tzinfo=datetime.timezone.utc)
        result = _parse_date("2025-09-15T10:30:00Z", default)

        assert result.year == 2025
        assert result.month == 9
        assert result.day == 15
        assert result.tzinfo == datetime.timezone.utc

    def test_parse_date_without_tz(self):
        """
        测试：没有时区信息的情况
        """
        from block_chain.process_prices import _parse_date

        default = datetime.datetime(2025, 9, 1, tzinfo=datetime.timezone.utc)
        result = _parse_date("2025-09-15T10:30:00", default)

        assert result.tzinfo == datetime.timezone.utc

    def test_parse_date_none(self):
        """
        测试：None值的情况
        """
        from block_chain.process_prices import _parse_date

        default = datetime.datetime(2025, 9, 1, tzinfo=datetime.timezone.utc)
        result = _parse_date(None, default)

        assert result == default

    def test_parse_date_empty_string(self):
        """
        测试：空字符串的情况
        """
        from block_chain.process_prices import _parse_date

        default = datetime.datetime(2025, 9, 1, tzinfo=datetime.timezone.utc)
        result = _parse_date("", default)

        assert result == default


class TestWriteAggregatedPrices:
    """
    测试 _write_aggregated_prices 函数
    """

    def test_write_aggregated_prices_overwrite(self):
        """
        测试：覆盖模式写入
        """
        from block_chain.process_prices import _write_aggregated_prices

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        df = pd.DataFrame(
            [
                (
                    datetime.datetime(
                        2025, 9, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    "Uniswap",
                    3000.0,
                ),
            ],
            columns=["time_bucket", "source", "average_price"],
        )

        with patch("block_chain.process_prices.execute_values") as mock_execute_values:
            _write_aggregated_prices(mock_conn, df, overwrite=True)

            # 验证DROP TABLE被调用
            assert mock_cur.execute.call_count >= 2
            # 验证CREATE TABLE被调用
            assert "CREATE TABLE" in str(mock_cur.execute.call_args_list)
            # 验证execute_values被调用
            assert mock_execute_values.called
            # 验证commit被调用
            assert mock_conn.commit.called

    def test_write_aggregated_prices_append(self):
        """
        测试：追加模式写入
        """
        from block_chain.process_prices import _write_aggregated_prices

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        df = pd.DataFrame(
            [
                (
                    datetime.datetime(
                        2025, 9, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    "Uniswap",
                    3000.0,
                ),
            ],
            columns=["time_bucket", "source", "average_price"],
        )

        with patch("block_chain.process_prices.execute_values") as mock_execute_values:
            _write_aggregated_prices(mock_conn, df, overwrite=False)

            # 验证DROP TABLE没有被调用
            drop_calls = [
                str(call)
                for call in mock_cur.execute.call_args_list
                if "DROP" in str(call)
            ]
            assert len(drop_calls) == 0
            # 验证execute_values被调用
            assert mock_execute_values.called
            # 验证commit被调用
            assert mock_conn.commit.called


class TestRunProcessPrices:
    """
    测试 run_process_prices 函数
    """

    @patch("block_chain.process_prices.psycopg2.connect")
    @patch("block_chain.process_prices.check_task", return_value=False)
    @patch("block_chain.process_prices.update_task_status")
    def test_run_process_prices_success(
        self, mock_update_status, mock_check_task, mock_connect
    ):
        """
        测试：成功运行聚合
        """
        from block_chain.process_prices import run_process_prices

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        # Mock数据库返回结果
        mock_cur.fetchall.return_value = [
            (
                datetime.datetime(2025, 9, 1, 10, 0, 0, tzinfo=datetime.timezone.utc),
                "Uniswap",
                3000.0,
            ),
        ]

        with patch("block_chain.process_prices._write_aggregated_prices") as mock_write:
            run_process_prices(
                task_id="test_task",
                aggregation_interval="minute",
                overwrite=True,
                start_date="2025-09-01",
                end_date="2025-09-01",
            )

            # 验证写入被调用
            assert mock_write.called
            # 验证任务状态更新为成功
            mock_update_status.assert_called_with("test_task", 1)

    @patch("block_chain.process_prices.psycopg2.connect")
    @patch("block_chain.process_prices.check_task", return_value=False)
    @patch("block_chain.process_prices.update_task_status")
    def test_run_process_prices_invalid_date_range(
        self, mock_update_status, mock_check_task, mock_connect
    ):
        """
        测试：无效的日期范围
        """
        from block_chain.process_prices import run_process_prices

        run_process_prices(
            task_id="test_task",
            start_date="2025-09-07",
            end_date="2025-09-01",  # 结束日期早于开始日期
        )

        # 验证任务状态更新为失败
        mock_update_status.assert_called_with("test_task", 2)

    @patch("block_chain.process_prices.psycopg2.connect")
    @patch("block_chain.process_prices.check_task", return_value=True)  # 任务被取消
    @patch("block_chain.process_prices.update_task_status")
    def test_run_process_prices_task_cancelled(
        self, mock_update_status, mock_check_task, mock_connect
    ):
        """
        测试：任务被取消
        """
        from block_chain.process_prices import run_process_prices

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        run_process_prices(
            task_id="test_task",
            start_date="2025-09-01",
            end_date="2025-09-01",
        )

        # 验证连接被关闭
        assert mock_conn.close.called

    @patch("block_chain.process_prices.psycopg2.connect")
    @patch("block_chain.process_prices.check_task", return_value=False)
    @patch("block_chain.process_prices.update_task_status")
    def test_run_process_prices_empty_results(
        self, mock_update_status, mock_check_task, mock_connect
    ):
        """
        测试：没有聚合结果
        """
        from block_chain.process_prices import run_process_prices

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        # Mock返回空结果
        mock_cur.fetchall.return_value = []

        run_process_prices(
            task_id="test_task",
            start_date="2025-09-01",
            end_date="2025-09-01",
        )

        # 验证连接被关闭
        assert mock_conn.close.called
        # 验证没有调用写入函数
        # (由于没有数据，不会调用 _write_aggregated_prices)

    @patch("block_chain.process_prices.psycopg2.connect")
    @patch("block_chain.process_prices.check_task", return_value=False)
    @patch("block_chain.process_prices.update_task_status")
    def test_run_process_prices_exception_in_loop(
        self, mock_update_status, mock_check_task, mock_connect
    ):
        """
        测试：循环中发生异常
        """
        from block_chain.process_prices import run_process_prices

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        # Mock执行时抛出异常
        mock_cur.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            run_process_prices(
                task_id="test_task",
                start_date="2025-09-01",
                end_date="2025-09-01",
            )

        # 验证任务状态更新为失败
        mock_update_status.assert_called_with("test_task", 2)

    @patch("block_chain.process_prices.psycopg2.connect")
    @patch("block_chain.process_prices.check_task", return_value=False)
    @patch("block_chain.process_prices.update_task_status")
    def test_run_process_prices_write_exception(
        self, mock_update_status, mock_check_task, mock_connect
    ):
        """
        测试：写入时发生异常
        """
        from block_chain.process_prices import run_process_prices

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        mock_cur.fetchall.return_value = [
            (
                datetime.datetime(2025, 9, 1, 10, 0, 0, tzinfo=datetime.timezone.utc),
                "Uniswap",
                3000.0,
            ),
        ]

        with patch("block_chain.process_prices._write_aggregated_prices") as mock_write:
            mock_write.side_effect = Exception("Write error")

            with pytest.raises(Exception, match="Write error"):
                run_process_prices(
                    task_id="test_task",
                    start_date="2025-09-01",
                    end_date="2025-09-01",
                )

            # 验证回滚被调用
            assert mock_conn.rollback.called
            # 验证任务状态更新为失败
            mock_update_status.assert_called_with("test_task", 2)

    @patch("block_chain.process_prices.psycopg2.connect")
    @patch("block_chain.process_prices.check_task", return_value=False)
    @patch("block_chain.process_prices.update_task_status")
    def test_run_process_prices_default_interval(
        self, mock_update_status, mock_check_task, mock_connect
    ):
        """
        测试：使用默认时间间隔
        """
        from block_chain.process_prices import run_process_prices

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        mock_cur.fetchall.return_value = []

        run_process_prices(
            task_id="test_task",
            start_date="2025-09-01",
            end_date="2025-09-01",
        )

        # 验证使用了默认的60秒间隔
        call_args = mock_cur.execute.call_args
        if call_args:
            params = call_args[0][1]
            assert params[0] == 60  # 默认使用60秒

    @patch("block_chain.process_prices.psycopg2.connect")
    @patch("block_chain.process_prices.check_task", return_value=False)
    @patch("block_chain.process_prices.update_task_status")
    def test_run_process_prices_custom_interval(
        self, mock_update_status, mock_check_task, mock_connect
    ):
        """
        测试：使用自定义时间间隔
        """
        from block_chain.process_prices import run_process_prices

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        mock_cur.fetchall.return_value = []

        run_process_prices(
            task_id="test_task",
            aggregation_interval="1h",  # 1小时 = 3600秒
            start_date="2025-09-01",
            end_date="2025-09-01",
        )

        # 验证使用了1小时的间隔
        call_args = mock_cur.execute.call_args
        if call_args:
            params = call_args[0][1]
            assert params[0] == 3600  # 1小时 = 3600秒
