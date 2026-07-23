# xycut接口和 JSON 格式

## 创建转写任务

脚本入口优先：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/transcribe.py "<source_path>"
```

接口等价请求：

```json
{
  "source_path": "<source_path>",
  "engine": "volcengine"
}
```

`engine` 可选：

- `sensevoice`
- `local`
- `volcengine`
- `online`

如果选择火山在线 ASR 且失败，xycut后端会自动兜底到本地 SenseVoice。

## 保存自动预审结果

优先调用：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_auto_review.py <task_id> "<task_dir>/analysis_merged.json"
```

预审 JSON：

```json
{
  "delete_sentences": [],
  "delete_word_indices": [],
  "reasons": {},
  "word_text_overrides": {},
  "reasons": {},
  "notes": ""
}
```

## 保存 Agent 字幕编排

Agent 先生成：

```text
<task_dir>/agent/agent_subtitle_plan.json
```

再通过脚本保存：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_agent_subtitle_plan.py <task_id> "<task_dir>/agent/agent_subtitle_plan.json"
```

保存短字幕接口请求：

```json
{
  "task_id": "<task_id>",
  "enabled": true,
  "source": "agent_generated",
  "lines": ["事情是这样的", "一个客户问我"]
}
```

保存字幕编排接口请求：

```json
{
  "task_id": "<task_id>",
  "plan": {
    "enabled": true,
    "source": "agent_generated",
    "items": []
  }
}
```

这两个接口只负责保存，不负责 AI 生成。

## 保存短字幕（仅手动文本）

推荐：

```json
{
  "task_id": "<task_id>",
  "lines": ["事情是这样的", "一个客户问我"],
  "source": "agent_generated"
}
```

兼容：

```json
{
  "task_id": "<task_id>",
  "short_subtitles": {
    "enabled": true,
    "lines": ["事情是这样的", "一个客户问我"],
    "source": "agent_generated"
  }
}
```

明确关闭：

```json
{
  "task_id": "<task_id>",
  "enabled": false,
  "source": "user_skipped"
}
```

空请求不会覆盖现有短字幕。

## 导入 Agent 素材结果

优先调用：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/import_material_result.py <task_id> "agent/v8_image_material_result.json"
```

接口等价请求：

```json
{
  "task_id": "<task_id>",
  "result_path": "agent/v8_image_material_result.json"
}
```

追加单个素材：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/append_material_asset.py <task_id> <line_id> "<asset_json或asset_json文件路径>"
```

单个素材最小结构：

```json
{
  "asset_id": "gen_20260618_001",
  "type": "image",
  "source": "minimax",
  "file_path": "materials/line_0001/gen_20260618_001/source.jpg",
  "thumb_path": "materials/line_0001/gen_20260618_001/thumb.jpg",
  "preview_path": "materials/line_0001/gen_20260618_001/source.jpg"
}
```
