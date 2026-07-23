#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import os


FILLER_WORDS = {"嗯", "呃", "啊", "额", "呃呃", "嗯嗯"}
LEADING_FILLERS = {"然后", "那么", "好的", "对", "呃", "嗯", "啊"}


def load_task_paths_from_transcript(transcript_json):
    task_dir = os.path.dirname(os.path.abspath(transcript_json))
    config_path = os.path.join(task_dir, "task_config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"缺少 task_config.json，无法定位 rule_prefill.json: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        task_config = json.load(f)
    return task_config.get("paths") or {}


def iter_words(transcript):
    for segment in transcript.get("segments") or []:
        words = segment.get("words") or []
        for pos, word in enumerate(words):
            if word.get("idx") is None:
                continue
            yield segment, words, pos, word


def word_text(word):
    return str(word.get("text") or word.get("word") or "").strip()


def main():
    parser = argparse.ArgumentParser(description="xycut保守规则预选：明显口癖词/句首填充词")
    parser.add_argument("transcript_json")
    parser.add_argument("output_json", nargs="?", default="")
    args = parser.parse_args()

    with open(args.transcript_json, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    delete_words = set()
    reasons = {}

    for segment, words, pos, word in iter_words(transcript):
        text = word_text(word)
        idx = int(word["idx"])
        if text in FILLER_WORDS:
            delete_words.add(idx)
            reasons[f"word_{idx}"] = "规则预选：明显口癖词"
            continue
        if pos <= 1 and text in LEADING_FILLERS and len(words) >= 6:
            delete_words.add(idx)
            reasons[f"word_{idx}"] = "规则预选：句首填充词"

    payload = {
        "delete_sentences": [],
        "delete_word_indices": sorted(delete_words),
        "reasons": reasons,
        "notes": "规则预选只标明显口癖；不确定内容交给 Agent 和审核台。",
    }
    paths = load_task_paths_from_transcript(args.transcript_json)
    output_json = args.output_json or paths.get("rule_prefill_json")
    if not output_json:
        raise RuntimeError("task_config.json 缺少 paths.rule_prefill_json")
    os.makedirs(os.path.dirname(os.path.abspath(output_json)), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "output": os.path.abspath(output_json),
        "delete_word_indices": len(payload["delete_word_indices"]),
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
