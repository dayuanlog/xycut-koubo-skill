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
  "style_hint": "优先搜索竖屏视频，没有视频再用图片"
}
```

Agent 生成素材：

```json
{
  "task_id": "<task_id>",
  "material_source_mode": "generated",
  "style_hint": "使用任务配置里的第三方 API 生成竖屏图片"
}
```

对应接口：

```text
POST http://127.0.0.1:23568/api/workflow/v8/agent-image-materials/prompt
```

使用已分类素材库前，先导出轻量索引：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/export_material_library_index.py <task_id>
```

接口等价请求：

```json
{
  "task_id": "<task_id>",
  "material_path_index": 0,
  "limit": 5000
}
```

对应接口：

```text
POST http://127.0.0.1:23568/api/workflow/v8/agent-material-library/export
```

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

已分类素材库素材可以使用 `source_path`，导入时xycut会复制到任务目录：

```json
{
  "task_id": "<task_id>",
  "source": "agent_library",
  "lines": [
    {
      "line_id": "line_0001",
      "asset_id": "library_0001",
      "type": "video",
      "source_path": "D:/素材库/餐饮/牛肉火锅.mp4",
      "prompt": "选择原因或匹配关键词",
      "status": "success"
    }
  ]
}
```

## 未分类素材分析缓存

未分类素材库使用素材目录下的 `material-analysis-cache.json`，不要和已分类素材库的 `material-cache.json` 混用。

同步素材目录，找出新增、变化、删除的素材：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/sync_unclassified_material_index.py "<material_dir>"
```

接口等价请求：

```json
{
  "material_dir": "D:/素材库/未分类旅游素材"
}
```

对应接口：

```text
POST http://127.0.0.1:23568/api/workflow/v8/agent-material-analysis/sync
```

返回里的 `pending_materials` 是需要 Agent 补充画面分析的素材。保存单个素材分析：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_unclassified_material_analysis.py "<material_dir>" "<material_id>" "<analysis_json或analysis文件路径>"
```

接口等价请求：

```json
{
  "material_dir": "D:/素材库/未分类旅游素材",
  "material_id": "m_abc123456789",
  "analysis": {
    "summary": "潮汕牛肉火锅店内近景，锅底沸腾，适合美食口播",
    "keywords": ["潮汕", "牛肉火锅", "美食"]
  }
}
```

对应接口：

```text
POST http://127.0.0.1:23568/api/workflow/v8/agent-material-analysis/save
```

为当前任务导出给 Agent 匹配使用的压缩索引：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/export_unclassified_material_match_index.py <task_id> "<material_dir>"
```

接口等价请求：

```json
{
  "task_id": "<task_id>",
  "material_dir": "D:/素材库/未分类旅游素材",
  "max_direct_items": 100,
  "candidates_per_line": 20
}
```

对应接口：

```text
POST http://127.0.0.1:23568/api/workflow/v8/agent-material-analysis/export
```

未分类素材最终导入结果只需要写 `material_id`，xycut 会从 `material-analysis-cache.json` 反查完整路径并复制素材：

```json
{
  "task_id": "<task_id>",
  "source": "agent_unclassified",
  "material_dir": "D:/素材库/未分类旅游素材",
  "lines": [
    {
      "line_id": "line_0001",
      "material_id": "m_abc123456789",
      "prompt": "这一行讲潮汕美食，选择牛肉火锅画面",
      "status": "success"
    }
  ]
}
```
