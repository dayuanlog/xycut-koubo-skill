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


def load_analysis(value):
    if os.path.isfile(value):
        with open(value, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return json.loads(value)


def main():
    parser = argparse.ArgumentParser(description="保存 Agent 对未分类素材的视觉分析")
    parser.add_argument("material_dir")
    parser.add_argument("material_id")
    parser.add_argument("analysis_json", help="JSON 字符串或 JSON 文件路径，需包含 summary，可选 keywords")
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    args = parser.parse_args()

    result = post_json(args.base_url.rstrip("/") + "/api/workflow/v8/agent-material-analysis/save", {
        "material_dir": args.material_dir,
        "material_id": args.material_id,
        "analysis": load_analysis(args.analysis_json),
    })
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
