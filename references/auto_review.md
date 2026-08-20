# 模式 A：Agent 自动预审

目标：让 Agent 先完成一轮口播预审，把明显重复、残句、卡顿、口癖和 ASR 修正建议写回xycut；最终仍由用户在xycut页面确认。

## A0. 判断是否已有xycut任务

如果用户给的是xycut任务目录，并要求“继续分析逐字稿”“口播剪辑审核”“预审口误/重复/错字”，说明前端可能已经完成转写。此时不要重新转写，先检查：

```text
<task_dir>/transcript.json
```

如果存在，直接进入 A2。

只有用户给的是原始音视频路径时，才执行 A1 创建转写任务。

## A1. 创建xycut转写任务

标准入口：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/transcribe.py "<source_path>"
```

多个音视频片段按用户给出的顺序一起传入：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/transcribe.py "<part_01.mp4>" "<part_02.mp4>" "<part_03.mp4>"
```

如果用户没有明确顺序，优先按文件名排序；仍不确定时先询问用户。

不要手动合成完整视频，也不要分别转写再拼时间戳。xycut后端会生成连续音频和来源映射：

```text
source_audio.wav
source_parts.json
```

后续转写、波形、静音和审核时间轴基于连续音频；剪映草稿画面会根据 `source_parts.json` 映射回原始视频片段。

脚本会调用：

```text
POST http://127.0.0.1:23568/api/workflow/v8/transcribe
```

返回后记录：

- `task_id`
- `task_dir`
- `transcript_path`
- `review_url`

## A2. 准备 Agent 分块分析

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/prepare_analysis.py "<task_dir>/transcript.json"
```

它会在 `<task_dir>/agent/chunks/` 生成：

```text
manifest.json
analysis_instructions.md
chunk_001.json
chunk_001.md
...
```

Agent 按 chunk 分析，不要把长口播一次性塞进一个回复。

如果 V8 全局词典里有词条，脚本会额外生成：

```text
<task_dir>/agent/asr_glossary.json
```

并在 `manifest.json` 写入 `asr_glossary_terms` 和 `asr_glossary_path`。这些词条只用于辅助判断明显 ASR 错字、同音错字、专有名词识别错误；不要为了匹配词典强行替换原文。

可选规则预选：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/rule_prefill.py "<task_dir>/transcript.json"
```

如果生成了 `agent/rule_prefill.json`，它只是候选提示。Agent 必须先复核里面的删除项；确认不会破坏原文后，才可以参与合并。没有把握时不要合并规则预选结果。

需要快速核对某个词的 `idx,text,start,end` 时，使用轻量词表脚本，不要直接读取很大的 chunk JSON：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/print_chunk_words.py "<task_dir>/agent/chunks" --idx-start 120 --idx-end 140
```

也可以按句子 index 查看：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/print_chunk_words.py "<task_dir>/agent/chunks" --sentence-index 12
```

## A3. 每个 chunk 的输出格式

每个 chunk 输出纯 JSON：

```json
{
  "delete_sentences": [],
  "delete_word_indices": [],
  "word_text_overrides": {},
  "reasons": {},
  "notes": ""
}
```

字段说明：

- `delete_sentences`：整句删除，使用句子 `index`。
- `delete_word_indices`：词级/字级删除，使用词的全局 `idx`。
- `word_text_overrides`：明显 ASR 错字修正，key 使用词的全局 `idx`，value 使用修正后的文字。
- `reasons` 和 `notes` 只是说明，不会真正删除。要删除必须写入 `delete_sentences` 或 `delete_word_indices`。
- 如果本任务存在 `agent/asr_glossary.json` 或 `manifest.asr_glossary_terms`，分析错字时应参考这些词条，但只能在原文明显识别错误且不改变原意时使用。

不要编造索引，只能使用当前 chunk 出现的 `index` 和 `idx`。

## A4. 预审判断规则

### 输入前提

- 文本来自 ASR，可能有同音错词、专有名词错误或英文名误写。
- 不要因为看到错字、错专有名词就判断为口误并删除。
- 明显是 ASR 错字但原话表达流畅时，应保留并写入 `word_text_overrides`。
- Agent 的任务是判断原话是否重复、残句、卡顿、口癖，并给出必要 ASR 修正。

### 整句删除

可以整句删除：

- 明显重复重说，且后面已有更完整表达。
- 未说完的残句。
- 只有语气词、停顿词、无实际内容的句子。
- 明确读错后马上重读的错误句。
- 相邻句开头 5 个字以上相同，且语义明显重复时，删除前面版本，保留最后完整版本。
- 连续 3 句及以上同义重说时，只保留最完整、最顺的一句。
- 完整句 + 残句 + 完整句，前后内容相近时，优先删除前面的完整句和中间残句，保留后面的完整句。
- 句子是前文的部分重复、否定纠正、词被打断后重说时，通常整句删除。

### 重复内容处理

- 重复判断以完整语义为主，不只看字面相似。
- 重复读了两遍或多遍时，默认保留最后一遍完整表达，删除前面的试读、卡顿、残句或不完整版本。
- 如果最后一遍明显不完整、读错或语义不顺，则保留语义最完整、表达最顺的一遍。
- 不要因为前面先出现就保留前面；口播重读通常以后面修正后的版本为准。

### 短残句 + 完整句

- 如果某句很短，像下一句的起头、试读或卡顿，且下一句完整承接并扩展它，应删除短残句，保留完整句。
- 示例：`一开始` + `一开始我以为大家焦虑的是流量`，删除前面的 `一开始`。
- 不能机械套用“开头相同就删除”。如果短句本身有独立信息量，或下一句讲的是不同信息，则保留。

### 词级删除

可以词级删除：

- 不影响语义的口癖词，如“呃”“嗯”“啊”“这个”“那个”。
- 明显卡顿重复的单词。
- 多余的开头拖音或结尾口头禅。
- 句首无实质作用的过渡词：然后、那么、好、好吧、哦、对、呢、哎、那。
- 句中无实质作用的填充词：其实、就、也、大概、哦、呃、那个、这个、就是、呢。
- 冗余引导短语：大家可以看到、你看、给大家看一下、比如说你看一下、我可以告诉你、你明白吗。
- 句尾无功能废词：对、呢、哦、啊。
- 前半段说错、后半段纠正时，优先删除前半段，保留后半段。

### “然后”判定

- 删除：句首单纯起头、句中口癖式连接、连续多个“然后”。
- 保留：真正表达“先 A 后 B”的时间顺序，或“做了 X 然后才 Y”的因果关系。

### 必须保留

- 有信息量的正常表达。
- 删除后会破坏语义、节奏或情绪的词。
- 虽然不完美但具有个人风格的自然口语。
- 列举、固定搭配、英文词组、自然重复强调，例如“一个一个地”。
- 不确定是否删除时保留，交给用户在 xycut审核台确认。

## A5. 合并并写回xycut审核状态

多个 chunk 分析完成后，先合并：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/merge_analysis.py analysis_merged.json "<chunk_result_001.json>" "<chunk_result_002.json>" --transcript "<task_dir>/transcript.json"
```

如果规则预选结果已经复核，可以一起传入：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/merge_analysis.py analysis_merged.json \
  "<task_dir>/agent/rule_prefill.json" \
  "<task_dir>/agent/chunks/analysis_chunk_001.json" \
  --transcript "<task_dir>/transcript.json"
```

只要传了 `--transcript`，相对输出 `analysis_merged.json` 会自动落到 `<task_dir>`。

然后写回xycut审核状态：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_auto_review.py <task_id> "<task_dir>/analysis_merged.json"
```

`save_auto_review.py` 会：

- 把 `delete_sentences/delete_word_indices` 转成 xycut前端可见的删除标记。
- 把 `word_text_overrides` 转成 xycut的单字修正。
- 调用 `/api/workflow/v8/review-state/save`。
- 自动生成 `final_copy.json` 和 `final_copy.txt`。

某个 chunk 分析失败时，写空结构并继续后续 chunk。最坏情况下也要保存空 `analysis_merged.json`，让审核台能打开。

## A6. 返回审核链接

完成后返回：

```text
http://127.0.0.1:23568/v8/<task_id>
```

告诉用户：已经完成转写和 AI 自动预审，打开链接后确认 AI 的删除和修正建议。
