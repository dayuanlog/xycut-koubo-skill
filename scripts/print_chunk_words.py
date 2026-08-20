#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Print a compact word table from xycut Agent chunk JSON files."""

import argparse
import json
import os


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def iter_chunk_files(path):
    path = os.path.abspath(str(path or "").strip().strip('"'))
    if os.path.isdir(path):
        for name in sorted(os.listdir(path)):
            if name.startswith("chunk_") and name.endswith(".json"):
                yield os.path.join(path, name)
        return
    yield path


def in_range(value, start, end):
    if value is None:
        return False
    if start is not None and value < start:
        return False
    if end is not None and value > end:
        return False
    return True


def compact_time(value):
    if value is None:
        return ""
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def main():
    parser = argparse.ArgumentParser(description="按 idx 或句子范围查看 chunk_*.json 里的词表")
    parser.add_argument("chunk", help="chunk_*.json 文件或 agent/chunks 目录")
    parser.add_argument("--idx-start", type=int, default=None)
    parser.add_argument("--idx-end", type=int, default=None)
    parser.add_argument("--sentence-index", type=int, default=None)
    parser.add_argument("--limit", type=int, default=120)
    args = parser.parse_args()

    rows = []
    for path in iter_chunk_files(args.chunk):
        data = load_json(path)
        chunk_id = data.get("chunk_id") or os.path.basename(path)
        for sentence in data.get("sentences") or []:
            sentence_index = sentence.get("index")
            if args.sentence_index is not None and sentence_index != args.sentence_index:
                continue
            sentence_text = sentence.get("text") or ""
            for word in sentence.get("words") or []:
                if word.get("idx") is None:
                    continue
                idx = int(word["idx"])
                if args.idx_start is not None or args.idx_end is not None:
                    if not in_range(idx, args.idx_start, args.idx_end):
                        continue
                rows.append({
                    "chunk": chunk_id,
                    "sentence": sentence_index,
                    "idx": idx,
                    "text": str(word.get("text") or word.get("word") or ""),
                    "start": compact_time(word.get("start")),
                    "end": compact_time(word.get("end")),
                    "sentence_text": sentence_text,
                })

    limit = max(1, int(args.limit or 120))
    print("chunk\tsentence\tidx\ttext\tstart\tend\tsentence_text")
    for row in rows[:limit]:
        print(
            f"{row['chunk']}\t{row['sentence']}\t{row['idx']}\t{row['text']}\t"
            f"{row['start']}\t{row['end']}\t{row['sentence_text']}"
        )
    if len(rows) > limit:
        print(f"... truncated: {len(rows) - limit} more rows")


if __name__ == "__main__":
    main()
