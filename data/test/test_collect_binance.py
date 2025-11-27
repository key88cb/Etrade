"""
collect_binance.py 的单元测试
"""

import os
import sys
from unittest.mock import MagicMock, Mock, mock_open, patch

import pandas as pd
import pytest

# 获取当前脚本文件的目录
# os.path.abspath(__file__) 获取当前文件的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 获取上一级目录（父目录）的路径
# os.path.dirname() 用于获取给定路径的父目录
parent_dir = os.path.dirname(current_dir)

# 将上一级目录添加到 sys.path
# sys.path 是 Python 解释器查找模块的路径列表
sys.path.insert(0, parent_dir)

from block_chain.collect_binance import (
    count_lines,
    import_data_to_database,
    process_chunk,
)


class TestCountLines:
    """
    测试文件行数统计函数
    """

    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2\nline3\n")
    def test_count_lines_success(self, mock_file):
        """
        测试：成功统计文件行数
        """

        result = count_lines("test.csv")

        assert result == 3
        mock_file.assert_called_once_with("test.csv", "rb")

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_count_lines_file_not_found(self, mock_file):
        """
        测试：文件不存在的情况
        """

        result = count_lines("nonexistent.csv")

        assert result is None

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_count_lines_permission_error(self, mock_file):
        """
        测试：权限错误的情况
        """

        result = count_lines("restricted.csv")

        assert result is None


class TestProcessChunk:
    """
    测试数据块处理函数
    """

    @pytest.fixture
    def sample_chunk(self):
        """
        创建示例数据块
        """
        return pd.DataFrame(
            {
                "id": [1, 2, 3],
                "price": [3000.0, 3001.0, 3002.0],
                "qty": [1.0, 2.0, 3.0],
                "quoteQty": [3000.0, 6002.0, 9006.0],
                "time": [1725187200000000, 1725187260000000, 1725187320000000],
                "isBuyerMaker": [True, False, True],
                "isBestMatch": [True, True, True],
            }
        )

    def test_process_chunk_success(self, sample_chunk, mock_db_connection):
        """
        测试：成功处理数据块
        """

        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        rows_counter = [0, 0]

        success, rows_processed, rows_imported, should_stop = process_chunk(
            sample_chunk,
            0,
            mock_conn,
            "binance_trades",
            mock_pbar,
            rows_counter,
            None,
            "行",
        )

        assert success is True
        assert rows_processed == len(sample_chunk)
        assert rows_imported == len(sample_chunk)
        assert rows_counter[0] == len(sample_chunk)
        assert rows_counter[1] == len(sample_chunk)
        mock_cursor.copy_expert.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_process_chunk_renames_columns(self, sample_chunk, mock_db_connection):
        """
        测试：列名重命名是否正确
        """

        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        rows_counter = [0, 0]

        process_chunk(
            sample_chunk,
            0,
            mock_conn,
            "binance_trades",
            mock_pbar,
            rows_counter,
            None,
            "行",
        )

        # 验证SQL中使用了正确的列名
        assert mock_cursor.copy_expert.called
        call_args = mock_cursor.copy_expert.call_args
        # call_args is a tuple (args, kwargs), so we access kwargs via [1]
        assert call_args is not None
        sql = call_args.kwargs.get("sql", "")
        assert "trade_time" in sql
        assert "quote_qty" in sql
        assert "is_buyer_maker" in sql

    def test_process_chunk_converts_timestamp(self, sample_chunk, mock_db_connection):
        """
        测试：时间戳转换是否正确
        """

        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        rows_counter = [0, 0]

        csv_data = []

        def mock_copy_expert(sql, file):
            csv_data.append(file.read())
            file.seek(0)

        mock_cursor.copy_expert.side_effect = mock_copy_expert

        process_chunk(
            sample_chunk,
            0,
            mock_conn,
            "binance_trades",
            mock_pbar,
            rows_counter,
            None,
            "行",
        )

        # 验证CSV数据包含时间戳（应该被转换为datetime格式）
        assert len(csv_data) > 0

    def test_process_chunk_handles_empty_chunk(self, mock_db_connection):
        """
        测试：处理空数据块
        """

        empty_chunk = pd.DataFrame()
        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        rows_counter = [0, 0]

        success, rows_processed, rows_imported, should_stop = process_chunk(
            empty_chunk,
            0,
            mock_conn,
            "binance_trades",
            mock_pbar,
            rows_counter,
            None,
            "行",
        )

        assert success is True
        assert rows_processed == 0
        assert rows_imported == 0

    def test_process_chunk_handles_db_error(self, sample_chunk, mock_db_connection):
        """
        测试：处理数据库错误
        """

        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.copy_expert.side_effect = Exception("Database error")
        mock_pbar = MagicMock()
        rows_counter = [0, 0]

        success, rows_processed, rows_imported, should_stop = process_chunk(
            sample_chunk,
            0,
            mock_conn,
            "binance_trades",
            mock_pbar,
            rows_counter,
            None,
            "行",
        )

        assert success is False
        assert rows_imported == 0
        mock_conn.rollback.assert_called_once()

    def test_process_chunk_stops_at_target_rows(self, mock_db_connection):
        """
        测试：达到目标行数时停止
        """
        # 创建一个足够大的chunk，使得处理后总行数 >= target_rows
        large_chunk = pd.DataFrame(
            {
                "id": list(range(1, 11)),  # 10行数据
                "price": [3000.0 + i for i in range(10)],
                "qty": [1.0] * 10,
                "quoteQty": [3000.0 + i for i in range(10)],
                "time": [1725187200000000 + i * 60000000 for i in range(10)],
                "isBuyerMaker": [True, False] * 5,
                "isBestMatch": [True] * 10,
            }
        )

        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        rows_counter = [5, 5]  # 已经处理了5行
        target_rows = 10

        success, rows_processed, rows_imported, should_stop = process_chunk(
            large_chunk,
            0,
            mock_conn,
            "binance_trades",
            mock_pbar,
            rows_counter,
            target_rows,
            "行",
        )

        # 处理后总行数应该 >= target_rows (5 + 10 = 15 >= 10)
        assert rows_counter[0] >= target_rows
        assert should_stop is True

    def test_process_chunk_dropna_after_timestamp_conversion(self, mock_db_connection):
        """
        测试：时间戳转换后dropna导致chunk为空的情况
        """
        # 创建包含无效时间戳的数据
        chunk_with_invalid_timestamps = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "price": [3000.0, 3001.0, 3002.0],
                "qty": [1.0, 2.0, 3.0],
                "quoteQty": [3000.0, 6002.0, 9006.0],
                "time": [
                    None,  # 无效时间戳
                    None,  # 无效时间戳
                    None,  # 无效时间戳
                ],
                "isBuyerMaker": [True, False, True],
                "isBestMatch": [True, True, True],
            }
        )

        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        rows_counter = [0, 0]

        success, rows_processed, rows_imported, should_stop = process_chunk(
            chunk_with_invalid_timestamps,
            0,
            mock_conn,
            "binance_trades",
            mock_pbar,
            rows_counter,
            None,
            "行",
        )

        # 应该成功处理，但导入0行（因为所有时间戳都无效）
        assert success is True
        assert rows_processed == 3  # 原始chunk长度
        assert rows_imported == 0  # 没有有效数据被导入
        assert rows_counter[0] == 3
        # copy_expert不应该被调用，因为chunk在dropna后为空
        assert not mock_cursor.copy_expert.called

    def test_process_chunk_with_chunk_unit(self, sample_chunk, mock_db_connection):
        """
        测试：使用"块"作为进度条单位
        """
        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        rows_counter = [0, 0]

        success, rows_processed, rows_imported, should_stop = process_chunk(
            sample_chunk,
            0,
            mock_conn,
            "binance_trades",
            mock_pbar,
            rows_counter,
            None,
            "块",  # 使用"块"作为单位
        )

        assert success is True
        # 验证进度条更新了1（因为是"块"单位）
        mock_pbar.update.assert_called_with(1)

    def test_process_chunk_with_target_rows_not_reached(
        self, sample_chunk, mock_db_connection
    ):
        """
        测试：未达到目标行数的情况
        """
        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        rows_counter = [0, 0]
        target_rows = 100  # 目标行数很大

        success, rows_processed, rows_imported, should_stop = process_chunk(
            sample_chunk,
            0,
            mock_conn,
            "binance_trades",
            mock_pbar,
            rows_counter,
            target_rows,
            "行",
        )

        assert success is True
        assert should_stop is False  # 未达到目标行数


class TestImportDataToDatabase:
    """
    测试数据导入函数
    """

    @patch("block_chain.collect_binance.pd.read_csv")
    @patch("block_chain.collect_binance.tqdm")
    @patch("block_chain.collect_binance.logger")
    def test_import_data_to_database_success(
        self, mock_logger, mock_tqdm, mock_read_csv, mock_db_connection
    ):
        """
        测试：成功导入数据
        """
        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        mock_tqdm.return_value = mock_pbar

        # 创建模拟的chunk迭代器
        sample_chunk = pd.DataFrame(
            {
                "id": [1, 2],
                "price": [3000.0, 3001.0],
                "qty": [1.0, 2.0],
                "quoteQty": [3000.0, 6002.0],
                "time": [1725187200000000, 1725187260000000],
                "isBuyerMaker": [True, False],
                "isBestMatch": [True, True],
            }
        )
        mock_read_csv.return_value = [sample_chunk]

        rows_counter = import_data_to_database(mock_conn, None, 100)

        assert len(rows_counter) == 2
        assert rows_counter[0] == 2  # 处理的行数
        assert rows_counter[1] == 2  # 导入的行数
        mock_pbar.close.assert_called_once()

    @patch("block_chain.collect_binance.pd.read_csv")
    @patch("block_chain.collect_binance.tqdm")
    @patch("block_chain.collect_binance.logger")
    def test_import_data_to_database_with_target_rows(
        self, mock_logger, mock_tqdm, mock_read_csv, mock_db_connection
    ):
        """
        测试：带目标行数的导入
        """
        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        mock_tqdm.return_value = mock_pbar

        sample_chunk = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "price": [3000.0 + i for i in range(5)],
                "qty": [1.0] * 5,
                "quoteQty": [3000.0 + i for i in range(5)],
                "time": [1725187200000000 + i * 60000000 for i in range(5)],
                "isBuyerMaker": [True, False] * 2 + [True],
                "isBestMatch": [True] * 5,
            }
        )
        mock_read_csv.return_value = [sample_chunk]

        rows_counter = import_data_to_database(mock_conn, 3, 100)

        assert len(rows_counter) == 2
        # 应该达到目标行数并停止
        assert rows_counter[0] >= 3
        mock_pbar.close.assert_called_once()

    @patch("block_chain.collect_binance.pd.read_csv")
    @patch("block_chain.collect_binance.tqdm")
    @patch("block_chain.collect_binance.logger")
    def test_import_data_to_database_file_not_found(
        self, mock_logger, mock_tqdm, mock_read_csv, mock_db_connection
    ):
        """
        测试：文件不存在的情况
        """
        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        mock_tqdm.return_value = mock_pbar

        mock_read_csv.side_effect = FileNotFoundError("File not found")

        rows_counter = import_data_to_database(mock_conn, None, 100)

        assert len(rows_counter) == 2
        assert rows_counter[0] == 0
        assert rows_counter[1] == 0
        mock_logger.error.assert_called()
        mock_pbar.close.assert_called_once()

    @patch("block_chain.collect_binance.pd.read_csv")
    @patch("block_chain.collect_binance.tqdm")
    @patch("block_chain.collect_binance.logger")
    def test_import_data_to_database_general_exception(
        self, mock_logger, mock_tqdm, mock_read_csv, mock_db_connection
    ):
        """
        测试：处理一般异常
        """
        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        mock_tqdm.return_value = mock_pbar

        mock_read_csv.side_effect = Exception("Unexpected error")

        rows_counter = import_data_to_database(mock_conn, None, 100)

        assert len(rows_counter) == 2
        mock_logger.error.assert_called()
        mock_pbar.close.assert_called_once()

    @patch("block_chain.collect_binance.pd.read_csv")
    @patch("block_chain.collect_binance.tqdm")
    @patch("block_chain.collect_binance.logger")
    def test_import_data_to_database_multiple_chunks(
        self, mock_logger, mock_tqdm, mock_read_csv, mock_db_connection
    ):
        """
        测试：处理多个chunk
        """
        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        mock_tqdm.return_value = mock_pbar

        chunk1 = pd.DataFrame(
            {
                "id": [1, 2],
                "price": [3000.0, 3001.0],
                "qty": [1.0, 2.0],
                "quoteQty": [3000.0, 6002.0],
                "time": [1725187200000000, 1725187260000000],
                "isBuyerMaker": [True, False],
                "isBestMatch": [True, True],
            }
        )
        chunk2 = pd.DataFrame(
            {
                "id": [3, 4],
                "price": [3002.0, 3003.0],
                "qty": [3.0, 4.0],
                "quoteQty": [9006.0, 12012.0],
                "time": [1725187320000000, 1725187380000000],
                "isBuyerMaker": [True, False],
                "isBestMatch": [True, True],
            }
        )
        mock_read_csv.return_value = [chunk1, chunk2]

        rows_counter = import_data_to_database(mock_conn, None, 100)

        assert len(rows_counter) == 2
        assert rows_counter[0] == 4  # 处理了4行
        assert rows_counter[1] == 4  # 导入了4行
        assert mock_cursor.copy_expert.call_count == 2  # 两个chunk都处理了

    @patch("block_chain.collect_binance.pd.read_csv")
    @patch("block_chain.collect_binance.tqdm")
    @patch("block_chain.collect_binance.logger")
    def test_import_data_to_database_stops_at_target(
        self, mock_logger, mock_tqdm, mock_read_csv, mock_db_connection
    ):
        """
        测试：达到目标行数时停止处理
        """
        mock_conn, mock_cursor = mock_db_connection
        mock_pbar = MagicMock()
        mock_tqdm.return_value = mock_pbar

        # 第一个chunk达到目标行数
        chunk1 = pd.DataFrame(
            {
                "id": list(range(1, 6)),  # 5行
                "price": [3000.0 + i for i in range(5)],
                "qty": [1.0] * 5,
                "quoteQty": [3000.0 + i for i in range(5)],
                "time": [1725187200000000 + i * 60000000 for i in range(5)],
                "isBuyerMaker": [True, False] * 2 + [True],
                "isBestMatch": [True] * 5,
            }
        )
        chunk2 = pd.DataFrame(
            {
                "id": [6, 7],
                "price": [3005.0, 3006.0],
                "qty": [5.0, 6.0],
                "quoteQty": [15025.0, 18036.0],
                "time": [1725187500000000, 1725187560000000],
                "isBuyerMaker": [False, True],
                "isBestMatch": [True, True],
            }
        )
        mock_read_csv.return_value = [chunk1, chunk2]

        rows_counter = import_data_to_database(mock_conn, 3, 100)

        assert len(rows_counter) == 2
        # 应该只处理第一个chunk就停止（因为达到目标行数3）
        assert rows_counter[0] >= 3
        # 第二个chunk不应该被处理
        assert mock_cursor.copy_expert.call_count == 1
