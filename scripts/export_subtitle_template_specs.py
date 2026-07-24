#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Export compact xycut Agent context through the running xycut backend API."""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8") or "{}")


def resolve_task_id_and_dir(task):
    value = str(task or "").strip().strip('"')
    if os.path.isdir(value):
        task_json = os.path.join(value, "task.json")
        task_id = ""
        if os.path.exists(task_json):
            task_id = str(load_json(task_json).get("task_id") or "").strip()
        return task_id or os.path.basename(os.path.abspath(value)), os.path.abspath(value)
    return value, ""


def build_context_url(base_url, task_id="", template_id=""):
    base = base_url.rstrip("/")
    query = {}
    if template_id:
        query["template_id"] = template_id
    if task_id:
        path = f"{base}/api/workflow/v8/agent-context/{urllib.parse.quote(task_id)}"
    else:
        path = f"{base}/api/workflow/v8/agent-context"
    if query:
        path += "?" + urllib.parse.urlencode(query)
    return path


def main():
    parser = argparse.ArgumentParser(description="导出 xycut Agent 字幕上下文")
    parser.add_argument("task", nargs="?", default="", help="xycut task_id 或任务目录")
    parser.add_argument("--template-id", default="", help="指定模板 ID，优先级高于任务记录")
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    args = parser.parse_args()

    task_id, task_dir = resolve_task_id_and_dir(args.task)
    url = build_context_url(args.base_url, task_id=task_id, template_id=str(args.template_id or "").strip())
    try:
        data = get_json(url)
    except Exception as error:
        raise RuntimeError(
            "无法从 xycut 后端导出 Agent 上下文。请确认 xycut 已启动，且端口/任务 ID 正确。"
            f" url={url} error={error}"
        )
    if data.get("status") != "success":
        raise RuntimeError(f"xycut Agent 上下文导出失败: {data}")
    if task_dir:
        data.setdefault("task_dir", task_dir)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
