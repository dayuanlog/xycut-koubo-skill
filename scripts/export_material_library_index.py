#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import os
import urllib.request


def post_json(url, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60 * 5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def iter_materials(data):
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
        return
    if not isinstance(data, dict):
        return
    for key in ("materials", "items", "assets", "data", "results"):
        value = data.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield item
            return
        if isinstance(value, dict):
            yield from iter_materials(value)
            return


def material_text(material):
    parts = []
    for key in ("asset_id", "id", "name", "title", "filename", "file_name", "source_path", "path", "type", "category"):
        value = material.get(key)
        if value:
            parts.append(str(value))
    tags = material.get("tags")
    if isinstance(tags, list):
        parts.extend(str(tag) for tag in tags)
    elif tags:
        parts.append(str(tags))
    for key in ("description", "summary", "note", "remark"):
        value = material.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts).lower()


def material_tags(material):
    tags = material.get("tags")
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()]
    if isinstance(tags, str):
        return [item.strip() for item in tags.replace("，", ",").split(",") if item.strip()]
    return []


def matches_filters(material, tags, query):
    text = material_text(material)
    if tags:
        current_tags = set(material_tags(material))
        if not any(tag in current_tags or tag.lower() in text for tag in tags):
            return False
    if query and query.lower() not in text:
        return False
    return True


def compact_material(material):
    source_path = str(material.get("source_path") or material.get("path") or material.get("file_path") or "").strip()
    name = str(material.get("name") or material.get("title") or material.get("filename") or os.path.basename(source_path) or "").strip()
    return {
        "asset_id": material.get("asset_id") or material.get("id") or "",
        "name": name,
        "type": material.get("type") or material.get("media_type") or "",
        "tags": material_tags(material),
        "source_path": source_path,
        "duration": material.get("duration") or material.get("duration_seconds") or "",
        "description": material.get("description") or material.get("summary") or material.get("note") or "",
    }


def apply_filters(result, tags, query, compact, top_per_tag):
    if not (tags or query or compact or top_per_tag):
        return result
    materials = [item for item in iter_materials(result) if matches_filters(item, tags, query)]
    if top_per_tag and tags:
        selected = []
        seen_ids = set()
        for tag in tags:
            count = 0
            tag_lower = tag.lower()
            for material in materials:
                ident = id(material)
                if ident in seen_ids:
                    continue
                if tag in set(material_tags(material)) or tag_lower in material_text(material):
                    selected.append(material)
                    seen_ids.add(ident)
                    count += 1
                    if count >= top_per_tag:
                        break
        materials = selected
    if compact:
        materials = [compact_material(item) for item in materials]
    output = dict(result) if isinstance(result, dict) else {"status": "success"}
    output["filtered_count"] = len(materials)
    output["materials"] = materials
    for key in ("items", "assets", "data", "results"):
        if key in output and key != "materials":
            output.pop(key, None)
    return output


def main():
    parser = argparse.ArgumentParser(description="导出xycut已分类素材库索引给 Agent 使用")
    parser.add_argument("task_id")
    parser.add_argument("--material-path-index", type=int, default=None)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--tag", "--tags", action="append", default=[], help="按标签筛选，可重复传入")
    parser.add_argument("--query", default="", help="按名称、路径、说明等文本筛选")
    parser.add_argument("--compact", action="store_true", help="只输出 Agent 常用字段")
    parser.add_argument("--top-per-tag", type=int, default=0, help="每个标签最多输出多少条")
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    args = parser.parse_args()

    payload = {
        "task_id": args.task_id,
        "limit": args.limit,
    }
    if args.material_path_index is not None:
        payload["material_path_index"] = args.material_path_index
    result = post_json(args.base_url.rstrip("/") + "/api/workflow/v8/agent-material-library/export", payload)
    result = apply_filters(result, args.tag, args.query.strip(), args.compact, max(0, args.top_per_tag))
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
