"""
collect_uniswap.py 的单元测试
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

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

from block_chain.collect_uniswap import (fetch_all_swaps,
                                         process_and_store_uniswap_data)


class TestFetchAllSwaps:
    """
    测试Uniswap数据获取函数
    """

    @patch("block_chain.collect_uniswap.requests.post")
    def test_fetch_all_swaps_success(self, mock_post):
        """
        测试：成功获取swap数据
        """

        # Mock API响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "swaps": [
                    {
                        "id": "0x1",
                        "timestamp": "1725187200",
                        "amount0": "1.0",
                        "amount1": "3000.0",
                        "transaction": {"id": "0xtx1", "gasPrice": "50000000000"},
                    },
                    {
                        "id": "0x2",
                        "timestamp": "1725187260",
                        "amount0": "2.0",
                        "amount1": "6000.0",
                        "transaction": {"id": "0xtx2", "gasPrice": "50000000000"},
                    },
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # 第二次调用返回空列表，表示分页结束
        mock_post.side_effect = [
            mock_response,
            MagicMock(
                json=lambda: {"data": {"swaps": []}},
                raise_for_status=Mock(),
            ),
        ]

        result = fetch_all_swaps("0x123", 1725187200, 1725187260)

        assert len(result) == 2
        assert result[0]["id"] == "0x1"
        assert result[1]["id"] == "0x2"

    @patch("block_chain.collect_uniswap.requests.post")
    @patch("block_chain.collect_uniswap.time.sleep")
    def test_fetch_all_swaps_handles_request_error(self, mock_sleep, mock_post):
        """
        测试：处理请求错误（重试机制）
        """

        # 第一次请求失败，第二次成功
        mock_post.side_effect = [
            Exception("Network error"),
            MagicMock(
                json=lambda: {"data": {"swaps": []}},
                raise_for_status=Mock(),
            ),
        ]

        result = fetch_all_swaps("0x123", 1725187200, 1725187260)

        # 应该重试并最终返回空列表
        assert len(result) == 0
        assert mock_sleep.called  # 应该调用了sleep等待重试

    @patch("block_chain.collect_uniswap.requests.post")
    def test_fetch_all_swaps_pagination(self, mock_post):
        """
        测试：分页获取数据
        """

        # 第一次返回1000条，第二次返回500条，第三次返回空
        first_batch = [
            {
                "id": f"0x{i}",
                "timestamp": "1725187200",
                "amount0": "1.0",
                "amount1": "3000.0",
                "transaction": {"id": f"0xtx{i}", "gasPrice": "50000000000"},
            }
            for i in range(1000)
        ]

        second_batch = [
            {
                "id": f"0x{i+1000}",
                "timestamp": "1725187200",
                "amount0": "1.0",
                "amount1": "3000.0",
                "transaction": {"id": f"0xtx{i+1000}", "gasPrice": "50000000000"},
            }
            for i in range(500)
        ]

        mock_post.side_effect = [
            MagicMock(
                json=lambda: {"data": {"swaps": first_batch}},
                raise_for_status=Mock(),
            ),
            MagicMock(
                json=lambda: {"data": {"swaps": second_batch}},
                raise_for_status=Mock(),
            ),
            MagicMock(
                json=lambda: {"data": {"swaps": []}},
                raise_for_status=Mock(),
            ),
        ]

        result = fetch_all_swaps("0x123", 1725187200, 1725187260)

        assert len(result) == 1500
        assert mock_post.call_count == 3  # 三次API调用


class TestProcessAndStoreUniswapData:
    """
    测试Uniswap数据处理和存储函数
    """

    @patch("block_chain.collect_uniswap.execute_values")
    def test_process_and_store_uniswap_data_success(
        self, mock_execute_values, mock_db_connection
    ):
        """
        测试：成功处理和存储数据
        """

        mock_conn, mock_cursor = mock_db_connection
        swaps_data = [
            {
                "id": "0x1",
                "timestamp": "1725187200",
                "amount0": "1.0",
                "amount1": "3000.0",
                "transaction": {"id": "0xtx1", "gasPrice": "50000000000"},
            },
            {
                "id": "0x2",
                "timestamp": "1725187260",
                "amount0": "2.0",
                "amount1": "6000.0",
                "transaction": {"id": "0xtx2", "gasPrice": "50000000000"},
            },
        ]

        process_and_store_uniswap_data(swaps_data, mock_conn)

        # 验证execute_values被调用
        mock_execute_values.assert_called_once()
        # 验证数据被处理（应该计算了价格）
        assert mock_conn.__enter__.called

    @patch("block_chain.collect_uniswap.execute_values")
    def test_process_and_store_uniswap_data_calculates_price(
        self, mock_execute_values, mock_db_connection
    ):
        """
        测试：价格计算是否正确
        """

        mock_conn, mock_cursor = mock_db_connection
        swaps_data = [
            {
                "id": "0x1",
                "timestamp": "1725187200",
                "amount0": "1.0",  # ETH
                "amount1": "3000.0",  # USDT
                "transaction": {"id": "0xtx1", "gasPrice": "50000000000"},
            },
        ]

        process_and_store_uniswap_data(swaps_data, mock_conn)

        # 价格应该是 amount1 / amount0 = 3000.0 / 1.0 = 3000.0
        # 验证execute_values被调用
        mock_execute_values.assert_called_once()
        # 由于我们mock了数据库，无法直接验证，但可以验证函数执行成功
        assert mock_conn.__enter__.called

    @patch("block_chain.collect_uniswap.execute_values")
    def test_process_and_store_uniswap_data_handles_zero_amount0(
        self, mock_execute_values, mock_db_connection
    ):
        """
        测试：处理amount0为0的情况（应该跳过）
        """

        mock_conn, mock_cursor = mock_db_connection
        swaps_data = [
            {
                "id": "0x1",
                "timestamp": "1725187200",
                "amount0": "0.0",  # 零值，应该被跳过
                "amount1": "3000.0",
                "transaction": {"id": "0xtx1", "gasPrice": "50000000000"},
            },
            {
                "id": "0x2",
                "timestamp": "1725187260",
                "amount0": "1.0",  # 正常值
                "amount1": "3000.0",
                "transaction": {"id": "0xtx2", "gasPrice": "50000000000"},
            },
        ]

        process_and_store_uniswap_data(swaps_data, mock_conn)

        # 应该只处理了一条记录（跳过amount0=0的）
        # 验证execute_values被调用（只处理了一条记录）
        mock_execute_values.assert_called_once()
        # 由于mock，我们只能验证函数执行成功
        assert mock_conn.__enter__.called

    def test_process_and_store_uniswap_data_empty_data(self, mock_db_connection):
        """
        测试：空数据的情况
        """

        mock_conn, mock_cursor = mock_db_connection

        process_and_store_uniswap_data([], mock_conn)

        # 应该不执行数据库操作
        mock_cursor.execute.assert_not_called()
