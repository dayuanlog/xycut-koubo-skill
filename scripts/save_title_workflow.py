#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Write Agent-generated xycut title text into review_state.json."""

import argparse
import json
import os
import sys


def _app_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _load_storage():
    app_dir = _app_dir()
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    from core.v8 import X02_task_storage as storage

    return storage


def _resolve_task(task_ref: str):
    storage = _load_storage()
    task_ref = os.path.abspath(task_ref) if os.path.isdir(task_ref) else task_ref.strip()
    if os.path.isdir(task_ref):
        task_path = os.path.join(task_ref, "task.json")
        if not os.path.exists(task_path):
            raise FileNotFoundError(f"任务目录缺少 task.json: {task_ref}")
        task = storage.read_json(task_path)
        task_id = str(task.get("task_id") or os.path.basename(task_ref)).strip()
        if not task_id:
            raise ValueError("无法从任务目录识别 task_id")
        return task_id, task_ref

    task_id = task_ref
    storage.require_task(task_id)
    return task_id, storage.get_task_dir(task_id)


def _read_title(value: str) -> str:
    if os.path.exists(value):
        with open(value, "r", encoding="utf-8-sig") as f:
            return f.read().strip()
    return str(value or "").strip()


def main():
    parser = argparse.ArgumentParser(description="保存xycut Agent 标题文本到 review_state.json")
    parser.add_argument("task", help="xycut task_id 或任务目录")
    parser.add_argument("title", help="标题文本，或保存标题文本的 .txt 文件路径")
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    args = parser.parse_args()

    storage = _load_storage()
    task_id, task_dir = _resolve_task(args.task)
    title = _read_title(args.title)
    if not title:
        raise ValueError("标题文本不能为空")

    review_state_path = storage.task_file(task_id, "review_state.json")
    state = storage.read_json(review_state_path) if os.path.exists(review_state_path) else {}
    if not isinstance(state, dict):
        state = {}
    settings = state.get("jianying_settings") if isinstance(state.get("jianying_settings"), dict) else {}
    settings["newstitle_content"] = title
    state["jianying_settings"] = settings
    state["updated_at"] = storage.now_iso()
    storage.write_json(review_state_path, state)

    base_url = args.base_url.rstrip("/")
    output = {
        "status": "success",
        "task_id": task_id,
        "task_dir": task_dir,
        "review_state_path": review_state_path,
        "title_line_count": len([line for line in title.splitlines() if line.strip()]),
        "review_url": f"{base_url}/v8/{task_id}",
    }
    print(json.dumps(output, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
