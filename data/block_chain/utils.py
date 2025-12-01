"""
工具函数
"""
import json
from typing import Any, Optional

from loguru import logger


def load_config_from_string(config_json: Optional[str]) -> dict[str, Any]:
    """
    从 JSON 字符串加载配置
    如果 config_json 为 None 或空字符串，返回空字典
    """
    if not config_json:
        return {}
    try:
        return json.loads(config_json)
    except json.JSONDecodeError as e:
        logger.warning(f"解析配置 JSON 失败: {e}, 返回空配置")
        return {}
