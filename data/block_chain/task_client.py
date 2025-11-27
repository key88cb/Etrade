"""
当前版本仅在本地打印日志，避免在脚本中重复处理 task_id、配置解析等逻辑。
"""

from __future__ import annotations

import json
import sys
import threading
import time
from typing import Any, Optional


class TaskClient:
    """
    封装任务状态/日志的上报逻辑，要替换为 gRPC 。
    参数：
        task_id: 任务 ID，可为空（脚本手工运行时）
    """

    def __init__(self, task_id: Optional[str] = None) -> None:
        self.task_id = task_id or "local-run"
        self._lock = threading.Lock()

    def update_status(
        self, status: str, message: Optional[str] = None, payload: Optional[dict] = None
    ) -> None:
        entry = {
            "task_id": self.task_id,
            "status": status,
            "message": message,
            "payload": payload or {},
        }
        self._emit("STATUS", entry)

    def log(self, level: str, message: str, extra: Optional[dict] = None) -> None:
        entry = {
            "task_id": self.task_id,
            "level": level.upper(),
            "message": message,
            "extra": extra or {},
        }
        self._emit("LOG", entry)

    def _emit(self, event: str, data: dict) -> None:
        with self._lock:
            sys.stdout.write(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {event} {json.dumps(data, ensure_ascii=False)}\n"
            )
            sys.stdout.flush()


def load_config_from_string(config_json: Optional[str]) -> dict[str, Any]:
    """
    描述：解析 JSON 字符串为空字典 方便脚本手工运行。
    参数：config_json: JSON 字符串
    返回值：dict
    """
    if not config_json:
        return {}
    if isinstance(config_json, dict):
        return config_json
    return json.loads(config_json)
