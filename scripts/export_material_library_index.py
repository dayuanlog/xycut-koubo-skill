#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import urllib.request


def post_json(url, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60 * 5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="导出xycut已分类素材库索引给 Agent 使用")
    parser.add_argument("task_id")
    parser.add_argument("--material-path-index", type=int, default=None)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    args = parser.parse_args()

    payload = {
        "task_id": args.task_id,
        "limit": args.limit,
    }
    if args.material_path_index is not None:
        payload["material_path_index"] = args.material_path_index
    result = post_json(args.base_url.rstrip("/") + "/api/workflow/v8/agent-material-library/export", payload)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
