#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Save Agent auto-review results into a xycut task.

This script is the bridge between Agent analysis and the xycut manual review UI.
It marks suggested deletions in review_state.json, writes ASR word corrections
as word_text_overrides, and lets xycut regenerate final_copy.json/final_copy.txt.
"""

import argparse
import json
import os
import re
import urllib.request


def load_json_lenient(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read().strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def request_json(url, payload=None):
    if payload is None:
        req = urllib.request.Request(url, method="GET")
    else:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60 * 5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def to_int_set(values):
    output = set()
    for value in values or []:
        try:
            item = int(value)
        except (TypeError, ValueError):
            continue
        if item >= 0:
            output.add(item)
    return output


def normalize_overrides(raw):
    output = {}
    if not isinstance(raw, dict):
        return output
    for key, value in raw.items():
        try:
            idx = int(key)
        except (TypeError, ValueError):
            continue
        text = str(value or "").strip()
        if text:
            output[idx] = text
    return output


def selected_page_ids(review_page, delete_sentences, delete_words):
    selected = set()
    words = review_page.get("words") or []
    for page_idx, word in enumerate(words):
        word_idx = word.get("idx")
        segment_index = word.get("segment_index")
        try:
            word_idx = int(word_idx)
        except (TypeError, ValueError):
            word_idx = None
        try:
            segment_index = int(segment_index)
        except (TypeError, ValueError):
            segment_index = None
        if word_idx in delete_words or segment_index in delete_sentences:
            selected.add(f"word-{page_idx}")
    return selected


def page_text_overrides(review_page, word_text_overrides):
    output = {}
    words = review_page.get("words") or []
    for page_idx, word in enumerate(words):
        try:
            word_idx = int(word.get("idx"))
        except (TypeError, ValueError):
            continue
        if word_idx in word_text_overrides:
            output[str(page_idx)] = word_text_overrides[word_idx]
    return output


def main():
    parser = argparse.ArgumentParser(description="保存xycut Agent 自动预审结果，并生成 final_copy")
    parser.add_argument("task_id")
    parser.add_argument("analysis_json")
    parser.add_argument("--base-url", default="http://127.0.0.1:23568")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    try:
        raw = load_json_lenient(args.analysis_json)
    except Exception as exc:
        raw = {"notes": f"Agent 分析 JSON 解析失败，已按空预审保存：{exc}"}
    if not isinstance(raw, dict):
        raw = {}

    delete_sentences = to_int_set(raw.get("delete_sentences"))
    delete_words = to_int_set(raw.get("delete_word_indices") or raw.get("delete_idx"))
    word_overrides = normalize_overrides(raw.get("word_text_overrides") or raw.get("text_overrides") or {})

    try:
        request_json(base_url + "/api/workflow/v8/analysis", {
            "task_id": args.task_id,
            "delete_sentences": sorted(delete_sentences),
            "delete_word_indices": sorted(delete_words),
            "reasons": raw.get("reasons") if isinstance(raw.get("reasons"), dict) else {},
            "notes": raw.get("notes") if isinstance(raw.get("notes"), str) else "",
        })
    except Exception:
        # review-state/save below is the authoritative write for xycut auto-review.
        pass

    review_page = request_json(base_url + f"/api/workflow/v8/review-page-data/{args.task_id}")
    state_resp = request_json(base_url + f"/api/workflow/v8/review-state/{args.task_id}")
    state = state_resp.get("state") if isinstance(state_resp.get("state"), dict) else {}

    selected = set(str(item) for item in (state.get("selected_ids") or []) if str(item or "").strip())
    selected |= selected_page_ids(review_page, delete_sentences, delete_words)

    text_overrides = state.get("word_text_overrides") if isinstance(state.get("word_text_overrides"), dict) else {}
    text_overrides.update(page_text_overrides(review_page, word_overrides))

    state.update({
        "task_id": args.task_id,
        "selected_ids": sorted(selected),
        "word_text_overrides": text_overrides,
        "agent_auto_review": {
            "source": os.path.abspath(args.analysis_json),
            "delete_sentences": sorted(delete_sentences),
            "delete_word_indices": sorted(delete_words),
            "word_text_overrides": {str(k): v for k, v in sorted(word_overrides.items())},
            "notes": raw.get("notes") if isinstance(raw.get("notes"), str) else "",
        },
    })
    if isinstance(review_page.get("review_lines"), list):
        state["review_lines"] = review_page["review_lines"]

    result = request_json(base_url + "/api/workflow/v8/review-state/save", {
        "task_id": args.task_id,
        "state": state,
    })
    result["review_url"] = base_url + f"/v8/{args.task_id}"
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
