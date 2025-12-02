"""
task.py 的单元测试
"""

import os
import sys
from unittest.mock import MagicMock, mock_open, patch

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

# 在导入前mock配置文件和数据库连接
import yaml

with patch(
    "builtins.open",
    mock_open(
        read_data="db:\n  host: localhost\n  port: 5432\n  database: test_db\n  username: test_user\n  password: test_password"
    ),
):
    with patch("yaml.safe_load", return_value=mock_config):
        with patch("psycopg2.connect"):
            from block_chain.task import check_task, update_task_status


class TestCheckTask:
    """
    测试 check_task 函数
    """

    @patch("block_chain.task.psycopg2.connect")
    def test_check_task_canceled(self, mock_connect):
        """
        测试：任务已被取消
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = lambda x: mock_conn
        mock_connect.return_value.__exit__ = lambda *args: None
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        # Mock返回已取消状态
        mock_cursor.fetchone.return_value = ("TASK_STATUS_CANCELED",)

        result = check_task("test_task_1")

        assert result is True
        mock_cursor.execute.assert_called_once()

    @patch("block_chain.task.psycopg2.connect")
    def test_check_task_not_canceled(self, mock_connect):
        """
        测试：任务未被取消
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = lambda x: mock_conn
        mock_connect.return_value.__exit__ = lambda *args: None
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        # Mock返回运行中状态
        mock_cursor.fetchone.return_value = ("TASK_STATUS_RUNNING",)

        result = check_task("test_task_2")

        assert result is False
        mock_cursor.execute.assert_called_once()

    @patch("block_chain.task.psycopg2.connect")
    @patch("block_chain.task.logger")
    def test_check_task_not_found(self, mock_logger, mock_connect):
        """
        测试：任务不存在
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = lambda x: mock_conn
        mock_connect.return_value.__exit__ = lambda *args: None
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        # Mock返回None（任务不存在）
        mock_cursor.fetchone.return_value = None

        result = check_task("nonexistent_task")

        assert result is True  # 任务不存在时返回True（视为已取消）
        mock_logger.error.assert_called_once()

    @patch("block_chain.task.psycopg2.connect")
    @patch("block_chain.task.logger")
    def test_check_task_database_error(self, mock_logger, mock_connect):
        """
        测试：数据库连接错误
        """
        # Mock连接时抛出异常
        mock_connect.side_effect = Exception("Database connection error")

        result = check_task("test_task_3")

        assert result is True  # 异常时返回True（视为已取消）
        mock_logger.error.assert_called_once()

    @patch("block_chain.task.psycopg2.connect")
    @patch("block_chain.task.logger")
    def test_check_task_query_error(self, mock_logger, mock_connect):
        """
        测试：查询执行错误
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = lambda x: mock_conn
        mock_connect.return_value.__exit__ = lambda *args: None
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        # Mock执行查询时抛出异常
        mock_cursor.execute.side_effect = Exception("Query execution error")

        result = check_task("test_task_4")

        assert result is True  # 异常时返回True（视为已取消）
        mock_logger.error.assert_called_once()


class TestUpdateTaskStatus:
    """
    测试 update_task_status 函数
    """

    @patch("block_chain.task.psycopg2.connect")
    def test_update_task_status_success(self, mock_connect):
        """
        测试：成功更新任务状态
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = lambda x: mock_conn
        mock_connect.return_value.__exit__ = lambda *args: None
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        update_task_status("test_task_1", "TASK_STATUS_COMPLETED")

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "UPDATE tasks" in call_args[0][0]
        assert call_args[0][1] == ("TASK_STATUS_COMPLETED", "test_task_1")

    @patch("block_chain.task.psycopg2.connect")
    def test_update_task_status_with_int_status(self, mock_connect):
        """
        测试：使用整数状态更新任务
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = lambda x: mock_conn
        mock_connect.return_value.__exit__ = lambda *args: None
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        update_task_status("test_task_2", 1)

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1] == (1, "test_task_2")

    @patch("block_chain.task.psycopg2.connect")
    @patch("block_chain.task.logger")
    def test_update_task_status_database_error(self, mock_logger, mock_connect):
        """
        测试：数据库连接错误
        """
        # Mock连接时抛出异常
        mock_connect.side_effect = Exception("Database connection error")

        update_task_status("test_task_3", "TASK_STATUS_FAILED")

        mock_logger.error.assert_called_once()

    @patch("block_chain.task.psycopg2.connect")
    @patch("block_chain.task.logger")
    def test_update_task_status_update_error(self, mock_logger, mock_connect):
        """
        测试：更新执行错误
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = lambda x: mock_conn
        mock_connect.return_value.__exit__ = lambda *args: None
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        # Mock执行更新时抛出异常
        mock_cursor.execute.side_effect = Exception("Update execution error")

        update_task_status("test_task_4", "TASK_STATUS_FAILED")

        mock_logger.error.assert_called_once()

    @patch("block_chain.task.psycopg2.connect")
    def test_update_task_status_task_id_conversion(self, mock_connect):
        """
        测试：任务ID类型转换（确保str(task_id)被调用）
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = lambda x: mock_conn
        mock_connect.return_value.__exit__ = lambda *args: None
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        # 使用整数任务ID
        update_task_status(12345, "TASK_STATUS_RUNNING")

        call_args = mock_cursor.execute.call_args
        assert call_args[0][1] == ("TASK_STATUS_RUNNING", "12345")
