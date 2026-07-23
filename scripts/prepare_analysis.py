#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import os


def load_task_paths_from_transcript(transcript_json):
    task_dir = os.path.dirname(os.path.abspath(transcript_json))
    config_path = os.path.join(task_dir, "task_config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"缺少 task_config.json，无法定位 agent/chunks: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        task_config = json.load(f)
    return task_config.get("paths") or {}


def flatten_words(segment):
    words = []
    for word in segment.get("words") or []:
        if word.get("idx") is None:
            continue
        words.append({
            "idx": int(word["idx"]),
            "text": word.get("text") or word.get("word") or "",
            "start": word.get("start"),
            "end": word.get("end"),
        })
    return words


def main():
    parser = argparse.ArgumentParser(description="把小映 transcript.json 整理成适合 Agent 分块预审的材料")
    parser.add_argument("transcript_json")
    parser.add_argument("output_dir", nargs="?", default="")
    parser.add_argument("--chunk-size", type=int, default=40)
    args = parser.parse_args()

    paths = load_task_paths_from_transcript(args.transcript_json)
    output_dir = args.output_dir or paths.get("agent_chunks_dir")
    if not output_dir:
        raise RuntimeError("task_config.json 缺少 paths.agent_chunks_dir")
    os.makedirs(output_dir, exist_ok=True)
    with open(args.transcript_json, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    sentences = []
    for fallback_index, segment in enumerate(transcript.get("segments") or []):
        words = flatten_words(segment)
        text = segment.get("text") or "".join(w["text"] for w in words)
        index = int(segment.get("index", fallback_index))
        sentences.append({
            "index": index,
            "text": text,
            "start": segment.get("start"),
            "end": segment.get("end"),
            "words": words,
        })

    chunk_size = max(10, args.chunk_size)
    chunks = []
    for offset in range(0, len(sentences), chunk_size):
        chunk = sentences[offset:offset + chunk_size]
        chunk_id = len(chunks) + 1
        data = {
            "chunk_id": chunk_id,
            "sentence_start": chunk[0]["index"] if chunk else 0,
            "sentence_end": chunk[-1]["index"] if chunk else 0,
            "sentences": chunk,
        }
        path = os.path.join(output_dir, f"chunk_{chunk_id:03d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        view_path = os.path.join(output_dir, f"chunk_{chunk_id:03d}.md")
        with open(view_path, "w", encoding="utf-8") as f:
            f.write(f"# Chunk {chunk_id:03d}\n\n")
            for sentence in chunk:
                word_indices = [w["idx"] for w in sentence["words"]]
                idx_span = f"{word_indices[0]}-{word_indices[-1]}" if word_indices else "-"
                f.write(f"[{sentence['index']}] {sentence['text']}\n")
                f.write(f"word_idx: {idx_span}\n\n")
        chunks.append({
            "chunk_id": chunk_id,
            "path": path,
            "view_path": view_path,
            "sentence_start": data["sentence_start"],
            "sentence_end": data["sentence_end"],
            "count": len(chunk),
        })

    manifest = {
        "task_id": transcript.get("task_id"),
        "source_path": transcript.get("source_path"),
        "transcript_path": os.path.abspath(args.transcript_json),
        "sentence_count": len(sentences),
        "chunk_size": chunk_size,
        "chunks": chunks,
        "output_schema": {
            "delete_sentences": [],
            "delete_word_indices": [],
            "word_text_overrides": {},
            "reasons": {},
            "notes": "",
        },
    }
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    prompt_path = os.path.join(output_dir, "analysis_instructions.md")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write("""# 小映长口播 Agent 自动预审说明

请按 chunk 顺序分析 `chunk_*.json`。

每个 chunk 只输出本组建议删除和修正的内容，最后合并成一个 JSON：

```json
{
  "delete_sentences": [],
  "delete_word_indices": [],
  "word_text_overrides": {},
  "reasons": {},
  "notes": ""
}
```

规则：

- 整句明显无效、重复、口误，写入 `delete_sentences`，使用句子 `index`。
- 只需要删除局部字词时，写入 `delete_word_indices`，使用词的全局 `idx`。
- 明显 ASR 错字、同音错词、专有名词识别错误，写入 `word_text_overrides`，key 使用词的全局 `idx`，value 使用修正后的单词文本。
- 只写 `reasons`、`notes` 或自然语言“建议删除”不会真正删除；要删除必须写入 `delete_sentences` 或 `delete_word_indices`。
- 输入文本来自 ASR，可能有同音错词或专有名词识别错误；这类问题优先写 `word_text_overrides`，不要因为转写错字就删除句子。
- 重复判断以完整语义为主，不只看字面相似；开头相似但提供不同信息的句子要保留。
- 重复读了两遍或多遍时，默认删除前面的试读/残句，保留最后一遍完整表达。
- 如果最后一遍不完整、读错或语义不顺，则保留语义最完整、表达最顺的一遍，删除其它重复版本。
- 不要因为前面先出现就保留前面；口播重读通常以后面修正后的版本为准。
- 短残句 + 完整句：如果某句很短、没有独立语义，像下一句的起头/试读/卡顿，且下一句完整承接并扩展它，删除短句，保留完整句。例如“一开始” + “一开始我以为大家焦虑的是流量”，删除前面的“一开始”。
- 不能机械套用“开头相同就删除”；如果两句都对文章主线有贡献，必须都保留。
- 相邻句开头 5 个字以上相同、连续多句同义重说、完整句+残句+完整句，通常删除前面版本，保留最后或最完整版本。
- 局部口癖优先词级删除：呃、嗯、啊、这个、那个、就是、其实、就、也、大概、句首无功能的然后/那么/那/对/好。
- “然后”如果是真实时间顺序或因果关系要保留；只是起头或口癖式连接才删除。
- 不确定就不要删，交给审核台人工处理。
- 不要输出 Markdown 包裹，最终只保存纯 JSON。
""")

    print(json.dumps({
        "manifest": manifest_path,
        "instructions": prompt_path,
        "chunks": len(chunks),
        "sentences": len(sentences),
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
