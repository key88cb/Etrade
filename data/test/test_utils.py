"""
utils.py 的单元测试
"""

import os
import sys
from unittest.mock import patch

import pytest

# 获取当前脚本文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上一级目录（父目录）的路径
parent_dir = os.path.dirname(current_dir)
# 将上一级目录添加到 sys.path
sys.path.insert(0, parent_dir)

from block_chain.utils import load_config_from_string


class TestLoadConfigFromString:
    """
    测试 load_config_from_string 函数
    """

    def test_load_config_from_string_valid_json(self):
        """
        测试：有效的JSON字符串
        """
        config_json = '{"strategy": {"initial_investment": 1000}, "batch_id": 1}'
        result = load_config_from_string(config_json)
        
        assert isinstance(result, dict)
        assert result["strategy"]["initial_investment"] == 1000
        assert result["batch_id"] == 1

    def test_load_config_from_string_none(self):
        """
        测试：None值
        """
        result = load_config_from_string(None)
        
        assert result == {}
        assert isinstance(result, dict)

    def test_load_config_from_string_empty_string(self):
        """
        测试：空字符串
        """
        result = load_config_from_string("")
        
        assert result == {}
        assert isinstance(result, dict)

    def test_load_config_from_string_whitespace_string(self):
        """
        测试：只包含空白字符的字符串
        """
        result = load_config_from_string("   ")
        
        assert result == {}
        assert isinstance(result, dict)

    def test_load_config_from_string_invalid_json(self):
        """
        测试：无效的JSON字符串
        """
        invalid_json = "{'invalid': json}"  # 使用单引号，不是有效的JSON
        
        with patch("block_chain.utils.logger") as mock_logger:
            result = load_config_from_string(invalid_json)
            
            assert result == {}
            assert isinstance(result, dict)
            # 验证警告日志被记录
            mock_logger.warning.assert_called_once()

    def test_load_config_from_string_malformed_json(self):
        """
        测试：格式错误的JSON字符串
        """
        malformed_json = '{"key": "value"'  # 缺少闭合括号
        
        with patch("block_chain.utils.logger") as mock_logger:
            result = load_config_from_string(malformed_json)
            
            assert result == {}
            assert isinstance(result, dict)
            mock_logger.warning.assert_called_once()

    def test_load_config_from_string_empty_json_object(self):
        """
        测试：空的JSON对象
        """
        result = load_config_from_string("{}")
        
        assert result == {}
        assert isinstance(result, dict)

    def test_load_config_from_string_nested_json(self):
        """
        测试：嵌套的JSON对象
        """
        nested_json = '''
        {
            "strategy": {
                "initial_investment": 1000,
                "binance_fee_rate": 0.001,
                "nested": {
                    "level": 3
                }
            },
            "batch_id": 1,
            "overwrite": true
        }
        '''
        result = load_config_from_string(nested_json)
        
        assert result["strategy"]["initial_investment"] == 1000
        assert result["strategy"]["binance_fee_rate"] == 0.001
        assert result["strategy"]["nested"]["level"] == 3
        assert result["batch_id"] == 1
        assert result["overwrite"] is True

    def test_load_config_from_string_with_array(self):
        """
        测试：包含数组的JSON
        """
        json_with_array = '{"items": [1, 2, 3], "name": "test"}'
        result = load_config_from_string(json_with_array)
        
        assert result["items"] == [1, 2, 3]
        assert result["name"] == "test"

    def test_load_config_from_string_with_special_characters(self):
        """
        测试：包含特殊字符的JSON
        """
        json_with_special = '{"message": "Hello\\nWorld", "path": "/usr/bin"}'
        result = load_config_from_string(json_with_special)
        
        assert result["message"] == "Hello\nWorld"
        assert result["path"] == "/usr/bin"

