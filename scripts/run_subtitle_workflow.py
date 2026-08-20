#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Run the current xycut V8 subtitle workflow.

This is equivalent to clicking "AI生成字幕" in the xycut V8 page.
"""

import argparse
import json
import os
import sys
import threading
import time
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
    with urllib.request.urlopen(req, timeout=60 * 10) as resp:
        return json.loads(resp.read().decode("utf-8") or "{}")


def post_json_with_progress(url, payload, label, interval=20):
    result_holder = {}
    error_holder = {}
    done = threading.Event()

    def worker():
        try:
            result_holder["result"] = post_json(url, payload)
        except Exception as exc:
            error_holder["error"] = exc
        finally:
            done.set()

    started = time.time()
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    while not done.wait(interval):
        elapsed = int(time.time() - started)
        print(f"{label} 已等待 {elapsed}s，请继续等待后端 AI 编排完成...", file=sys.stderr, flush=True)
    elapsed = int(time.time() - started)
    print(f"{label} 完成，耗时 {elapsed}s", file=sys.stderr, flush=True)
    if "error" in error_holder:
        raise error_holder["error"]
    return result_holder.get("result") or {}


def get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
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


def resolve_task_dir_from_context(base_url, task_id):
    if not task_id:
        return ""
    try:
        result = get_json(base_url.rstrip("/") + f"/api/workflow/v8/agent-context/{task_id}")
    except Exception:
        return ""
    candidates = [
        result.get("task_dir"),
        result.get("task_path"),
    ]
    context = result.get("context") if isinstance(result.get("context"), dict) else {}
    candidates.extend([
        context.get("task_dir"),
        context.get("task_path"),
    ])
    task = result.get("task") if isinstance(result.get("task"), dict) else {}
    candidates.extend([
        task.get("task_dir"),
        task.get("task_path"),
    ])
    for candidate in candidates:
        candidate = str(candidate or "").strip()
        if candidate and os.path.isdir(candidate):
            return os.path.abspath(candidate)
    return ""


def load_asr_glossary(task_dir):
    if not task_dir:
        return []
    candidates = [
        os.path.join(task_dir, "agent", "asr_glossary.json"),
        os.path.join(task_dir, "asr_glossary.json"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            data = load_json(path)
            if isinstance(data, dict):
                data = data.get("terms") or data.get("items") or []
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        except Exception:
            continue
    return []


def normalize_emphasis_ratio(value):
    try:
        ratio = int(round(float(value)))
    except (TypeError, ValueError):
        ratio = 30
    return max(10, min(60, ratio))


def main():
    parser = argparse.ArgumentParser(description="运行 xycut V8 AI 生成字幕")
    parser.add_argument("task", help="xycut task_id 或任务目录")
    parser.add_argument("--template-id", default="", help="指定口播模板 ID，例如 001")
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    parser.add_argument("--asr-glossary", default="", help="可选 ASR 词典 JSON 文件，数组或 {terms:[]}")
    parser.add_argument("--emphasis-ratio", default=30, type=int, help="03 重点预设目标比例，10-60，默认 30")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    task_id, task_dir = resolve_task_id(args.task)
    if not task_id:
        raise RuntimeError("无法识别 task_id")
    if not task_dir:
        task_dir = resolve_task_dir_from_context(base_url, task_id)

    if args.asr_glossary:
        data = load_json(args.asr_glossary)
        if isinstance(data, dict):
            data = data.get("terms") or data.get("items") or []
        asr_glossary = [str(item).strip() for item in data if str(item).strip()] if isinstance(data, list) else []
    else:
        asr_glossary = load_asr_glossary(task_dir)

    payload = {"task_id": task_id}
    emphasis_ratio = normalize_emphasis_ratio(args.emphasis_ratio)
    payload["emphasis_ratio"] = emphasis_ratio
    template_id = str(args.template_id or "").strip()
    if template_id:
        payload["koubo_template_id"] = template_id
        payload["v8_template_id"] = template_id
    if asr_glossary:
        payload["asr_glossary"] = asr_glossary

    result = post_json_with_progress(
        base_url + "/api/workflow/v8/subtitle-workflow/ai-generate",
        payload,
        "V8 AI 生成字幕",
    )
    if result.get("status") != "success":
        raise RuntimeError(result.get("message") or json.dumps(result, ensure_ascii=False))

    short_subtitles = result.get("short_subtitles") if isinstance(result.get("short_subtitles"), dict) else {}
    plan = result.get("plan") if isinstance(result.get("plan"), dict) else {}
    output = {
        "status": "success",
        "task_id": task_id,
        "task_dir": task_dir,
        "review_url": base_url + f"/v8/{task_id}",
        "short_subtitle_count": len(short_subtitles.get("lines") or []),
        "layout_item_count": len(plan.get("items") or []),
        "emphasis_ratio": int(result.get("emphasis_ratio") or emphasis_ratio),
        "ai_call_count": int(result.get("ai_call_count") or 0),
        "used_builtin_count": int(result.get("used_builtin_count") or 0),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

