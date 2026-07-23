#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import urllib.request


def post_json(url, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60 * 60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="调用小映口播转录 API")
    parser.add_argument("source_paths", nargs="+")
    parser.add_argument("--engine", default="")
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    args = parser.parse_args()

    if len(args.source_paths) == 1:
        payload = {"source_path": args.source_paths[0]}
    else:
        payload = {"source_paths": args.source_paths}
    if args.engine:
        payload["engine"] = args.engine
    result = post_json(args.base_url.rstrip("/") + "/api/workflow/v8/transcribe", payload)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
