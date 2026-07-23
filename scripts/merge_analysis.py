#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re


def load_task_paths_from_transcript(transcript_json):
    if not transcript_json:
        return {}
    task_dir = os.path.dirname(os.path.abspath(transcript_json))
    config_path = os.path.join(task_dir, "task_config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"缺少 task_config.json，无法定位合并输出: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        task_config = json.load(f)
    return task_config.get("paths") or {}


def load_json_lenient(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def to_int_list(values):
    output = []
    for value in values or []:
        try:
            item = int(value)
        except (TypeError, ValueError):
            continue
        if item >= 0:
            output.append(item)
    return output


def flatten_words(transcript):
    words = []
    for segment in transcript.get("segments") or []:
        for word in segment.get("words") or []:
            if word.get("idx") is not None:
                words.append(word)
    return words


def main():
    parser = argparse.ArgumentParser(description="合并小映分块 Agent 分析结果")
    parser.add_argument("output_json")
    parser.add_argument("analysis_files", nargs="+")
    parser.add_argument("--transcript", default="", help="可选：用于过滤越界句子/词 idx 的 transcript.json")
    args = parser.parse_args()

    valid_sentences = None
    valid_words = None
    if args.transcript and os.path.exists(args.transcript):
        transcript = load_json_lenient(args.transcript)
        valid_sentences = {int(s.get("index", i)) for i, s in enumerate(transcript.get("segments") or [])}
        valid_words = {int(w["idx"]) for w in flatten_words(transcript)}

    delete_sentences = set()
    delete_words = set()
    word_text_overrides = {}
    reasons = {}
    notes = []
    errors = []

    for path in args.analysis_files:
        try:
            data = load_json_lenient(path)
        except Exception as exc:
            errors.append(f"{os.path.basename(path)}: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{os.path.basename(path)}: root is not object")
            continue

        for idx in to_int_list(data.get("delete_sentences")):
            if valid_sentences is None or idx in valid_sentences:
                delete_sentences.add(idx)
        for idx in to_int_list(data.get("delete_word_indices") or data.get("delete_idx")):
            if valid_words is None or idx in valid_words:
                delete_words.add(idx)

        overrides = data.get("word_text_overrides") or data.get("text_overrides") or {}
        if isinstance(overrides, dict):
            for raw_idx, value in overrides.items():
                try:
                    idx = int(raw_idx)
                except (TypeError, ValueError):
                    continue
                text = str(value or "").strip()
                if text and (valid_words is None or idx in valid_words):
                    word_text_overrides[str(idx)] = text

        if isinstance(data.get("reasons"), dict):
            reasons.update(data["reasons"])
        if isinstance(data.get("notes"), str) and data["notes"].strip():
            notes.append(data["notes"].strip())

    payload = {
        "delete_sentences": sorted(delete_sentences),
        "delete_word_indices": sorted(delete_words),
        "word_text_overrides": word_text_overrides,
        "reasons": reasons,
        "notes": "\n".join(notes),
    }
    if errors:
        payload["notes"] = (payload["notes"] + "\n" if payload["notes"] else "") + "合并时跳过异常文件：" + "；".join(errors)

    output_json = args.output_json
    if args.transcript and not os.path.isabs(output_json):
        paths = load_task_paths_from_transcript(args.transcript)
        if os.path.basename(output_json) == "analysis_merged.json":
            output_json = paths.get("analysis_merged_json") or ""
        else:
            output_json = ""
        if not output_json:
            raise RuntimeError("相对输出路径必须通过 task_config.json 定位，目前仅支持 analysis_merged.json")
    os.makedirs(os.path.dirname(os.path.abspath(output_json)), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "output": os.path.abspath(output_json),
        "delete_sentences": len(payload["delete_sentences"]),
        "delete_word_indices": len(payload["delete_word_indices"]),
        "errors": errors,
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
