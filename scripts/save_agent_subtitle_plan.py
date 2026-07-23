#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import os
import urllib.request


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def post_json(url, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60 * 5) as resp:
        return json.loads(resp.read().decode("utf-8") or "{}")


def resolve_task_id(task):
    value = str(task or "").strip().strip('"')
    if os.path.isdir(value):
        task_json = os.path.join(value, "task.json")
        if os.path.exists(task_json):
            task_data = load_json(task_json)
            task_id = str(task_data.get("task_id") or "").strip()
            if task_id:
                return task_id, os.path.abspath(value)
        return os.path.basename(os.path.abspath(value)), os.path.abspath(value)
    return value, ""


def compact_text(value):
    return str(value or "").strip()


def plan_lines(plan):
    lines = []
    for item in plan.get("items") or []:
        if not isinstance(item, dict):
            continue
        text = compact_text(item.get("text"))
        if text:
            lines.append(text)
    return lines


def normalize_plan(plan):
    if not isinstance(plan, dict):
        raise ValueError("字幕编排结果必须是 JSON object")
    items = plan.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("字幕编排结果缺少 items")
    output_items = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        text = compact_text(item.get("text"))
        style_id = compact_text(item.get("style_id"))
        parts = item.get("parts") if isinstance(item.get("parts"), dict) else {}
        if not text or not style_id or not parts:
            raise ValueError(f"第 {index + 1} 条缺少 text/style_id/parts")
        next_item = dict(item)
        next_item["index"] = index
        next_item["text"] = text
        next_item["style_id"] = style_id
        next_item["parts"] = {str(k): compact_text(v) for k, v in parts.items() if compact_text(v)}
        output_items.append(next_item)
    if not output_items:
        raise ValueError("字幕编排结果没有可保存的 items")
    output = dict(plan)
    output["enabled"] = True
    output["source"] = "agent_generated"
    output["items"] = output_items
    return output


def main():
    parser = argparse.ArgumentParser(description="保存 Agent 生成的xycut字幕编排")
    parser.add_argument("task", help="xycut task_id 或任务目录")
    parser.add_argument("agent_plan_json", help="Agent 生成的 agent_subtitle_plan.json")
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    args = parser.parse_args()

    task_id, task_dir = resolve_task_id(args.task)
    if not task_id:
        raise RuntimeError("无法识别 task_id")
    plan = normalize_plan(load_json(args.agent_plan_json))
    lines = plan_lines(plan)
    if not lines:
        raise RuntimeError("没有可保存的短字幕 lines")

    base_url = args.base_url.rstrip("/")
    short_result = post_json(base_url + "/api/workflow/v8/short-subtitles/save", {
        "task_id": task_id,
        "enabled": True,
        "source": "agent_generated",
        "lines": lines,
    })
    plan_result = post_json(base_url + "/api/workflow/v8/subtitle-layout-plan/save", {
        "task_id": task_id,
        "plan": plan,
    })
    output = {
        "status": "success",
        "task_id": task_id,
        "task_dir": task_dir,
        "review_url": base_url + f"/v8/{task_id}",
        "short_subtitle_count": len(lines),
        "layout_item_count": len(plan.get("items") or []),
        "short_subtitles_path": short_result.get("short_subtitles_path"),
        "plan_path": plan_result.get("plan_path"),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
