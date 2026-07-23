#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
import urllib.request


def load_json_lenient(path_or_text):
    if os.path.exists(path_or_text):
        with open(path_or_text, "r", encoding="utf-8") as f:
            text = f.read().strip()
    else:
        text = path_or_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def compact_asset(asset):
    if not isinstance(asset, dict):
        return {}
    out = {}
    for key in ("asset_id", "type", "source", "file_path", "thumb_path", "preview_path"):
        value = str(asset.get(key) or "").strip()
        if value:
            out[key] = value
    return out


def post_json(url, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60 * 5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Append one xycut material asset without rewriting full material_plan.json.")
    parser.add_argument("task_id")
    parser.add_argument("line_id")
    parser.add_argument("asset_json", help="Asset JSON string or path to a JSON file")
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    args = parser.parse_args()

    asset = compact_asset(load_json_lenient(args.asset_json))
    result = post_json(args.base_url.rstrip("/") + "/api/workflow/v8/material-asset/append", {
        "task_id": args.task_id,
        "line_id": args.line_id,
        "asset": asset,
    })
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
