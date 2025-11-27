"""
Risk analysis placeholder.

仅保留结构，后续可以实现实际逻辑 反正之后要加其他的分析脚本也是这样加的
"""

import argparse
from typing import Optional

from .task_client import TaskClient, load_config_from_string


def run_analyze_risk(task_id: Optional[str] = None, config_json: Optional[str] = None):
    client = TaskClient(task_id)
    config = load_config_from_string(config_json)
    client.update_status("running", "未实现")
    # TODO: 实现风险分析逻辑
    client.update_status("success", "风险分析占位任务已完成", {"config": config})


def main():
    parser = argparse.ArgumentParser(description="风险分析任务占位实现")
    parser.add_argument("--task-id", dest="task_id", default=None)
    parser.add_argument("--config", dest="config", default=None)
    args = parser.parse_args()
    run_analyze_risk(args.task_id, args.config)


if __name__ == "__main__":
    main()
