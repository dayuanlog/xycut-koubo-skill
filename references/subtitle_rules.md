# 新版 V8 字幕编排规则

这份规则用于调试或人工生成 `agent_subtitle_plan.json`。正常情况下，优先调用 `scripts/run_subtitle_workflow.py`，让 xycut 后端完成当前 V8 四步 AI 编排。

## 不要做的事

- 不要生成 SRT 来冒充模板字幕。
- 不要直接覆盖 `short_subtitles.json` 或 `subtitle_layout_plan.json`。
- 不要用 Agent 自己拼一套字幕规则替代 xycut V8 后端工作流。
- 不要强制输出当前后端不需要的字段。
- 不要把英文字幕混在样式选择步骤里；新版后端有独立英文步骤。
- 不要直接读取完整模板 JSON 或解密模板。

## 字幕拆分

- 按语义拆，不按字数硬切。
- 01/02 适合短字幕，通常 6-10 个字左右，但以语义完整为准。
- 03 保留完整重点表达，不要提前拆得太碎。
- 不要把固定词、数字、单位、英文、地名、人名、品牌名拆断。
- 不要丢字、重复、乱序。

## 样式选择

- 01：单行默认，普通叙述、承接、解释。
- 02：单行强调，短促强调、提醒、轻转折、小重点。
- 03：重点预设，开头钩子、强利益点、价格数字、避坑提醒、反转结论、行动号召。
- 当前项目希望 01/02/03 更均衡，内容足够时可接近三分之一，但仍以语义为准。

## 关键词高亮

01/02 可以写 `highlight_ranges`：

```json
"highlight_ranges": [
  {"field": "main", "start": 2, "end": 5, "text": "关键词"}
]
```

规则：

- 关键词必须是原字幕中真实连续存在的词。
- 不是每句都需要关键词。
- 不要整句高亮。
- 通常 2-6 个字。
- 生成草稿时由小映 APP 当前模板处理关键词高亮样式。

也可以用兼容写法 `highlights`，保存时后端会尽量转成范围：

```json
"highlights": {"main": ["低成本"]}
```

## 03 重点预设

03 的核心是 `segments` + `theme`：

```json
{
  "text": "人均800玩转五天四夜",
  "style_id": "03",
  "parts": {"main": "人均800玩转五天四夜"},
  "segments": ["人均800", "玩转五天四夜"],
  "theme": "价格利益"
}
```

分段规则：

- 短内容 5 个字左右，通常 1 段。
- 中等内容 10 个字左右，通常 2 段。
- 长内容 12 个字以上，可拆 2-3 段。
- 根据语义拆分，不要平分。
- 不要拆坏明显词组、数字、英文、单位、时间范围、价格范围。
- `segments` 按顺序拼起来应等于 `text` 去标点后的内容。

8 个主题：

- `重点突出`
- `转折对比`
- `疑问悬疑`
- `提醒避坑`
- `正向结果`
- `惊讶冲击`
- `轻松幽默`
- `价格利益`

## 英文字幕

新版后端会独立生成英文副字幕。如果手动写计划，可以写：

```json
"parts": {
  "main": "现在私信我",
  "main_en": "DM me now"
}
```

或：

```json
"parts": {
  "main": "现在私信我",
  "text_2": "DM me now"
}
```

英文要短、自然、适合字幕点缀，不要改动中文。

## 保存

手动计划保存：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_agent_subtitle_plan.py <task_id> "<task_dir>/agent/agent_subtitle_plan.json"
```

默认自动编排：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/run_subtitle_workflow.py <task_id或task_dir>
```
