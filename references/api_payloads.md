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

`engine` 可选：`sensevoice`、`local`、`volcengine`、`online`。

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
  "notes": ""
}
```

## 新版 V8 AI 字幕编排

优先调用脚本：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/run_subtitle_workflow.py <task_id或task_dir>
```

接口请求：

```json
{
  "task_id": "<task_id>",
  "koubo_template_id": "001",
  "v8_template_id": "001",
  "emphasis_ratio": 30,
  "asr_glossary": ["专有名词"]
}
```

接口：

```text
POST /api/workflow/v8/subtitle-workflow/ai-generate
```

返回会包含：

```json
{
  "status": "success",
  "task_id": "<task_id>",
  "short_subtitles": {"enabled": true, "lines": []},
  "plan": {"enabled": true, "items": []},
  "emphasis_ratio": 30,
  "ai_call_count": 4
}
```

## 手动保存 Agent 字幕编排

只用于调试或用户明确给出计划：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_agent_subtitle_plan.py <task_id> "<task_dir>/agent/agent_subtitle_plan.json"
```

手动计划示例：

```json
{
  "enabled": true,
  "source": "agent_generated",
  "asset_workflow": true,
  "items": [
    {
      "text": "听我一句劝",
      "style_id": "01",
      "parts": {"main": "听我一句劝"},
      "highlight_ranges": [{"field": "main", "start": 2, "end": 4, "text": "一句"}]
    },
    {
      "text": "人均800玩转五天四夜",
      "style_id": "03",
      "parts": {"main": "人均800玩转五天四夜"},
      "segments": ["人均800", "玩转五天四夜"],
      "theme": "价格利益"
    }
  ]
}
```

`highlight_ranges` 只用于 01/02。03 使用样式个人预设，不要写 `highlight_ranges`、`highlights` 或 `parts.keyword`。

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
    "asset_workflow": true,
    "items": []
  }
}
```

## 导入 Agent 素材结果

生成素材协作提示词时，用 `material_source_mode` 明确素材来源，不要把几种来源混用。

已分类标签素材：

```json
{
  "task_id": "<task_id>",
  "material_source_mode": "classified",
  "material_path_index": 0,
  "style_hint": "优先使用真实视频素材"
}
```

未分类素材：

```json
{
  "task_id": "<task_id>",
  "material_source_mode": "unclassified",
  "unclassified_material_dir": "D:/素材库/未分类旅游素材",
  "style_hint": "优先使用真实视频素材，不足时再生成图片"
}
```

免费商业图库 / Pexels：

```json
{
  "task_id": "<task_id>",
  "material_source_mode": "pexels",
  "query": "business presentation"
}
```

导入接口：

```text
POST /api/workflow/v8/agent-image-materials/import
```

脚本入口：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/import_material_result.py <task_id> "<task_dir>/agent/v8_image_material_result.json"
```

## 写回新闻标题文本

标题文本写入草稿生成页的「封面与标题」模块。PowerShell 下推荐先保存为 UTF-8 文本文件，再传文件路径。

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_title_workflow.py <task_id> "<task_dir>/agent/newstitle.txt"
```

也可以传入文本文件：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_title_workflow.py <task_id> "<task_dir>/agent/newstitle.txt"
```

## 写回封面图片

封面图片必须是本地文件，推荐放在任务目录内部，例如 `<task_dir>/cover/agent_cover_001.png`。

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_cover_workflow.py <task_id> "<task_dir>/cover/agent_cover_001.png"
```

如果同时有封面标题，可以一起写入：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_cover_workflow.py <task_id> "<task_dir>/cover/agent_cover_001.png" --title-file "<task_dir>/agent/newstitle.txt"
```
