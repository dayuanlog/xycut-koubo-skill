#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
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


def clean_subtitle_display_text(value):
    text = compact_text(value)
    text = re.sub(r"[，。！？；：、,.!?;:]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def plan_lines(plan):
    lines = []
    for item in plan.get("items") or []:
        if not isinstance(item, dict):
            continue
        text = clean_subtitle_display_text(item.get("text"))
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
        text = clean_subtitle_display_text(item.get("text"))
        style_id = compact_text(item.get("style_id"))
        parts = item.get("parts") if isinstance(item.get("parts"), dict) else {}
        if not text or not style_id or not parts:
            raise ValueError(f"第 {index + 1} 条缺少 text/style_id/parts")
        next_item = dict(item)
        next_item["index"] = index
        next_item["text"] = text
        next_item["style_id"] = style_id
        next_parts = {}
        for key, value in parts.items():
            key = str(key)
            text_value = compact_text(value) if key.endswith("_en") or key in {"text_2", "text_2_left", "text_2_right"} else clean_subtitle_display_text(value)
            if text_value:
                next_parts[key] = text_value
        next_item["parts"] = next_parts
        output_items.append(next_item)
    if not output_items:
        raise ValueError("字幕编排结果没有可保存的 items")
    output = dict(plan)
    output["enabled"] = True
    output["source"] = "agent_generated"
    output["items"] = output_items
    return output


def build_plan_warnings(plan):
    items = plan.get("items") if isinstance(plan, dict) else []
    if not isinstance(items, list):
        return []
    warnings = []
    style03_count = 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if compact_text(item.get("style_id")) != "03":
            continue
        style03_count += 1
        parts = item.get("parts") if isinstance(item.get("parts"), dict) else {}
        if not compact_text(parts.get("keyword")):
            warnings.append(f"第 {index + 1} 条 03 缺少 parts.keyword")
        if not compact_text(item.get("effect_theme_id")):
            warnings.append(f"第 {index + 1} 条 03 缺少 effect_theme_id")
    if len(items) >= 20 and style03_count == 0:
        warnings.append("当前字幕超过 20 条但 03 数量为 0；如果模板支持 03，建议选择真正重点句使用。")
    return warnings


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
    warnings = build_plan_warnings(plan)
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
        "warnings": warnings,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
