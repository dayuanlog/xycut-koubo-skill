#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Save a manually prepared xycut V8 subtitle plan.

For normal use, prefer run_subtitle_workflow.py. This script is for debugging
or for plans explicitly provided by the user.
"""

import argparse
import json
import os
import re
import urllib.request


ENGLISH_KEYS = {"main_en", "left_en", "right_en", "text_2", "text_2_left", "text_2_right"}
THEMES = {"重点突出", "转折对比", "疑问悬疑", "提醒避坑", "正向结果", "惊讶冲击", "轻松幽默", "价格利益"}


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


def normalize_highlight_ranges(value):
    if not isinstance(value, list):
        return []
    output = []
    for item in value:
        if not isinstance(item, dict):
            continue
        try:
            start = int(item.get("start", 0))
            end = int(item.get("end", 0))
        except (TypeError, ValueError):
            continue
        field = str(item.get("field") or item.get("source") or "main").strip() or "main"
        if end > start:
            next_item = {"field": field, "start": start, "end": end}
            text = clean_subtitle_display_text(item.get("text") or "")
            if text:
                next_item["text"] = text
            output.append(next_item)
    return output


def normalize_parts(parts, text):
    if not isinstance(parts, dict):
        return {"main": text}
    output = {}
    for key, value in parts.items():
        key = str(key or "").strip()
        if not key:
            continue
        if key in ENGLISH_KEYS or key.endswith("_en"):
            text_value = compact_text(value)
        else:
            text_value = clean_subtitle_display_text(value)
        if text_value:
            output[key] = text_value
    if not output:
        output["main"] = text
    return output


def normalize_segments(value):
    if isinstance(value, str):
        raw = re.split(r"[|/，,、\n]+", value)
    elif isinstance(value, list):
        raw = value
    else:
        raw = []
    return [clean_subtitle_display_text(item) for item in raw if clean_subtitle_display_text(item)][:3]


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
        style_id = compact_text(item.get("style_id") or item.get("style"))
        if not text or not style_id:
            raise ValueError(f"第 {index + 1} 条缺少 text/style_id")
        next_item = dict(item)
        next_item["index"] = index
        next_item["text"] = text
        next_item["style_id"] = style_id
        next_item["parts"] = normalize_parts(item.get("parts"), text)
        ranges = normalize_highlight_ranges(item.get("highlight_ranges"))
        if ranges:
            next_item["highlight_ranges"] = ranges
        segments = normalize_segments(item.get("segments"))
        if segments:
            next_item["segments"] = segments
        theme = compact_text(item.get("theme") or item.get("asset_theme"))
        if theme:
            next_item["theme"] = theme
        for key in ("asset_match", "asset_match_en", "highlights", "source_indices", "personal_theme_source"):
            if key in item:
                next_item[key] = item[key]
        output_items.append(next_item)
    if not output_items:
        raise ValueError("字幕编排结果没有可保存的 items")
    output = dict(plan)
    output["enabled"] = True
    output["source"] = str(plan.get("source") or "agent_generated")
    output["asset_workflow"] = plan.get("asset_workflow", True)
    output["items"] = output_items
    return output


def build_plan_warnings(plan):
    items = plan.get("items") if isinstance(plan, dict) else []
    if not isinstance(items, list):
        return []
    warnings = []
    style03_count = 0
    for index, item in enumerate(items):
        if not isinstance(item, dict) or compact_text(item.get("style_id")) != "03":
            continue
        style03_count += 1
        segments = item.get("segments") if isinstance(item.get("segments"), list) else []
        if not segments:
            warnings.append(f"第 {index + 1} 条 03 缺少 segments，生成草稿前后端会尝试自动补算")
        theme = compact_text(item.get("theme"))
        if theme and theme not in THEMES:
            warnings.append(f"第 {index + 1} 条 03 theme 不是推荐 8 主题之一：{theme}")
        if not theme:
            warnings.append(f"第 {index + 1} 条 03 缺少 theme，生成草稿前后端会尝试自动补算")
    if len(items) >= 12 and style03_count == 0:
        warnings.append("当前字幕较多但 03 数量为 0；新版模板通常建议选择一部分真正重点句使用 03。")
    return warnings


def main():
    parser = argparse.ArgumentParser(description="保存手动 Agent 生成的 xycut V8 字幕编排")
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
        "source": plan.get("source") or "agent_generated",
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
