#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Write an Agent-generated cover image into a xycut task.

The image generation itself should be handled by a dedicated image skill. This
script only records an already-created image in cover_plan.json so the xycut page
can preview and use it when generating the Jianying draft.
"""

import argparse
import json
import os
import sys
import urllib.request


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def _read_json_if_exists(path: str):
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=60 * 5) as resp:
        return json.loads(resp.read().decode("utf-8") or "{}")


def _resolve_task_dir_from_context(task_id: str, base_url: str = "http://127.0.0.1:23568") -> str:
    task_id = str(task_id or "").strip()
    if not task_id:
        return ""
    try:
        result = _get_json(base_url.rstrip("/") + f"/api/workflow/v8/agent-context/{task_id}")
    except Exception:
        return ""
    candidates = [result.get("task_dir"), result.get("task_path")]
    context = result.get("context") if isinstance(result.get("context"), dict) else {}
    candidates.extend([context.get("task_dir"), context.get("task_path")])
    task = result.get("task") if isinstance(result.get("task"), dict) else {}
    candidates.extend([task.get("task_dir"), task.get("task_path")])
    for candidate in candidates:
        candidate = str(candidate or "").strip()
        if candidate and os.path.isdir(candidate):
            return os.path.abspath(candidate)
    return ""


def _looks_like_app_dir(path: str) -> bool:
    if not path:
        return False
    return os.path.exists(os.path.join(path, "core", "v8", "X02_task_storage.py"))


def _walk_parent_candidates(path: str):
    current = os.path.abspath(path)
    if os.path.isfile(current):
        current = os.path.dirname(current)
    while True:
        yield current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent


def _app_dir(task_ref: str = "") -> str:
    candidates = []
    for env_name in ("XYCUT_APP_DIR", "SHIPIN_ZHUSHOU_APP_DIR", "APP_DIR"):
        value = os.environ.get(env_name, "").strip()
        if value:
            candidates.append(value)

    task_ref = str(task_ref or "").strip().strip('"')
    if task_ref and not os.path.isdir(task_ref):
        task_dir = _resolve_task_dir_from_context(task_ref)
        if task_dir:
            task_ref = task_dir

    if task_ref and os.path.isdir(task_ref):
        task_config = _read_json_if_exists(os.path.join(task_ref, "task_config.json"))
        app_dir = str(task_config.get("app_dir") or "").strip()
        if app_dir:
            candidates.append(app_dir)
        candidates.extend(_walk_parent_candidates(task_ref))

    candidates.extend(_walk_parent_candidates(os.getcwd()))
    candidates.extend(_walk_parent_candidates(os.path.dirname(__file__)))

    for candidate in candidates:
        candidate = os.path.abspath(candidate)
        if _looks_like_app_dir(candidate):
            return candidate
    raise RuntimeError("无法定位小映 APP 目录。请在项目根目录运行，传入任务目录，或设置 XYCUT_APP_DIR。")


def _load_storage(task_ref: str = ""):
    app_dir = _app_dir(task_ref)
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    from core.v8 import X02_task_storage as storage

    return storage


def _resolve_task(task_ref: str):
    storage = _load_storage(task_ref)
    task_ref = os.path.abspath(task_ref) if os.path.isdir(task_ref) else task_ref.strip()
    if os.path.isdir(task_ref):
        task_path = os.path.join(task_ref, "task.json")
        if not os.path.exists(task_path):
            raise FileNotFoundError(f"任务目录缺少 task.json: {task_ref}")
        task = storage.read_json(task_path)
        task_id = str(task.get("task_id") or os.path.basename(task_ref)).strip()
        if not task_id:
            raise ValueError("无法从任务目录识别 task_id")
        return task_id, task_ref, task

    task_id = task_ref
    task = storage.require_task(task_id)
    return task_id, storage.get_task_dir(task_id), task


def _ensure_inside_task(task_dir: str, cover_path: str) -> str:
    cover_abs = os.path.abspath(cover_path)
    task_abs = os.path.abspath(task_dir)
    if not os.path.exists(cover_abs):
        raise FileNotFoundError(f"封面文件不存在: {cover_abs}")
    if not os.path.isfile(cover_abs):
        raise ValueError(f"封面路径不是文件: {cover_abs}")
    ext = os.path.splitext(cover_abs)[1].lower()
    if ext not in IMAGE_EXTS:
        raise ValueError(f"不支持的封面图片格式: {ext}")
    if os.path.commonpath([task_abs, cover_abs]) != task_abs:
        raise ValueError("cover_path 必须位于当前任务目录内，请先把封面图保存到任务目录")
    return cover_abs


def _task_rel_path(task_dir: str, path: str) -> str:
    rel = os.path.relpath(path, task_dir)
    return rel.replace("\\", "/")


def _read_title(value: str) -> str:
    if not value:
        return ""
    if os.path.exists(value):
        with open(value, "r", encoding="utf-8-sig") as f:
            return f.read().strip()
    return str(value or "").strip()


def _write_title(storage, task_id: str, title: str):
    title = (title or "").strip()
    if not title:
        return None
    review_state_path = storage.task_file(task_id, "review_state.json")
    state = storage.read_json(review_state_path) if os.path.exists(review_state_path) else {}
    if not isinstance(state, dict):
        state = {}
    settings = state.get("jianying_settings") if isinstance(state.get("jianying_settings"), dict) else {}
    settings["newstitle_content"] = title
    state["jianying_settings"] = settings
    state["updated_at"] = storage.now_iso()
    storage.write_json(review_state_path, state)
    return review_state_path


def main():
    parser = argparse.ArgumentParser(description="保存xycut Agent 封面图片到 cover_plan.json")
    parser.add_argument("task", help="xycut task_id 或任务目录")
    parser.add_argument("cover_path", help="已生成并保存到任务目录内的封面图片路径")
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    parser.add_argument("--source", default="agent_generated_cover")
    parser.add_argument("--title", default="", help="Optional cover/news title text to write into review_state.json")
    parser.add_argument("--title-file", default="", help="Optional UTF-8 title text file to write into review_state.json")
    args = parser.parse_args()

    storage = _load_storage(args.task)
    task_id, task_dir, _task = _resolve_task(args.task)
    cover_abs = _ensure_inside_task(task_dir, args.cover_path)
    cover_rel = _task_rel_path(task_dir, cover_abs)
    cover_plan_path = storage.task_file(task_id, "cover_plan.json")

    plan = {
        "task_id": task_id,
        "enabled": True,
        "cover_path": cover_rel,
        "file_path": cover_rel,
        "source": args.source,
        "updated_at": storage.now_iso(),
    }
    title = _read_title(args.title_file or args.title)
    if title:
        plan["title"] = title
    storage.write_json(cover_plan_path, plan)
    review_state_path = _write_title(storage, task_id, title)

    base_url = args.base_url.rstrip("/")
    output = {
        "status": "success",
        "task_id": task_id,
        "task_dir": task_dir,
        "cover_plan_path": cover_plan_path,
        "cover_path": cover_rel,
        "title_saved": bool(title),
        "review_state_path": review_state_path,
        "review_url": f"{base_url}/v8/{task_id}",
    }
    print(json.dumps(output, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
