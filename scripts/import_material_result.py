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
    parser = argparse.ArgumentParser(description="导入 Agent 素材结果到小映素材计划")
    parser.add_argument("task_id")
    parser.add_argument("result_path", help="agent/v8_image_material_result.json 或任务目录内的绝对路径")
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    args = parser.parse_args()

    result = post_json(args.base_url.rstrip("/") + "/api/workflow/v8/agent-image-materials/import", {
        "task_id": args.task_id,
        "result_path": args.result_path,
    })
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
