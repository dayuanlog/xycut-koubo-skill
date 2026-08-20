# xycut任务目录文件说明

任务目录是 xycut 后端、审核台和 Agent 的交接点。

默认位置：

```text
<剪映草稿目录>/临时文件/koubo_temp/<task_id>
```

## 根目录长期文件

这些文件代表任务状态或用户结果，不要随意删除。

| 文件 | 用途 |
| --- | --- |
| `task.json` | 任务基本信息 |
| `task_config.json` | Agent 使用的配置快照，含路径、API key、素材规格 |
| `source_audio.wav` | 多段口播源视频拼接后的连续音频，供转写、波形、静音和审核时间轴使用，单视频任务不存在 |
| `source_parts.json` | 多段口播源视频的来源顺序、原路径、时长和在连续时间轴中的起点；草稿画面会按它映射回原视频 |
| `transcript.json` | 转写结果，含句段、逐字时间戳 |
| `analysis_merged.json` | Agent 粗剪合并结果 |
| `review_state.json` | 审核台人工修改状态，含划线、恢复、分行、素材选择、草稿设置 |
| `review_lines.json` | 自然分行数据，可被审核台继续调整 |
| `final_copy.json` / `final_copy.txt` | 用户审核后最终保留文本，短字幕和素材规划优先读取 |
| `material_plan.json` | 素材规划和已下载/生成素材索引 |
| `cover_plan.json` | AI 封面计划 |
| `short_subtitles.json` | AI 或用户编辑后的短字幕文本 |
| `subtitle_layout_plan.json` | 新版 V8 字幕编排计划，包含 `style_id`、`parts`、`highlight_ranges`、`segments`、`theme`、`asset_match` |

## `agent/`

Agent 过程文件放这里，便于排查，但不是最终用户成果。

```text
agent/chunks/
agent/rule_prefill.json
agent/agent_subtitle_plan.json
agent/material_agent_input.json
agent/logs/
```

## `cache/`

xycut 后端可重建缓存放这里，不要把它们当成最终用户编辑结果。

```text
cache/review_page_data.json
cache/final_timeline.json
cache/line_timeline.json
cache/material_timeline.json
cache/final_audio_for_subtitle.wav
cache/short_subtitles_aligned.json
cache/line_talking_assets.json
```

## `materials/`

下载、截图、生成图、逐句口播合并素材、抠像结果都放这里。

规则：

- 使用相对任务目录路径写入计划文件。
- 每个素材用独立子目录，例如 `materials/line_0003/pexels_123/source.mp4`。
- 不要复用固定文件名覆盖旧素材。
- 不要把素材写到 skill 目录。
