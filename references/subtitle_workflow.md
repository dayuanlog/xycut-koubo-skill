# 模式 B：V8 字幕编排

目标：让当前 xycut V8 后端完成短字幕与剪映预设编排；Agent 负责检查任务状态、调用脚本/API、把结果写回，并把页面链接返回给用户。

字幕编排由 xycut V8 后端按当前口播模板完成。Agent 默认只负责调用工作流、检查结果、返回任务页面；模板资产、字幕样式、标题样式和封面样式由小映 APP 的模板配置决定。

## 核心边界

- xycut 后端是新版字幕编排和资产匹配的执行者。
- Agent 不生成 SRT 来代替 xycut 模板字幕。
- Agent 不直接覆盖 `short_subtitles.json` 或 `subtitle_layout_plan.json`。
- 默认不要手写整套字幕计划；优先调用当前 V8 后端 AI 工作流。
- 手动写回只用于调试、用户明确给出计划、或后端 AI 暂不可用的情况。

xycut 页面右侧字幕列读取：

```text
<task_dir>/short_subtitles.json
<task_dir>/subtitle_layout_plan.json
```

## B1. 任务前检查

先确认任务目录或 `task_id` 有效，并检查：

```text
<task_dir>/final_copy.json
<task_dir>/final_copy.txt
<task_dir>/review_state.json
<task_dir>/subtitle_layout_plan.json
```

如果没有 `final_copy.json/final_copy.txt`，不要生成字幕编排。告诉用户先完成「口播剪辑」审核并保存成稿。

如果已经存在用户手动编辑过的 `subtitle_layout_plan.json`，并且 `source` 类似 `user_edited`，不要覆盖，除非用户明确要求重新生成。

## B2. 默认执行方式：调用新版 V8 后端

优先运行：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/run_subtitle_workflow.py <task_id或task_dir>
```

可选指定模板：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/run_subtitle_workflow.py <task_id或task_dir> --template-id 001
```

可选控制 03 重点预设比例，默认 30。用户说“重点多一点”可用 40 或 45，用户说“重点少一点”可用 20：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/run_subtitle_workflow.py <task_id或task_dir> --emphasis-ratio 40
```

这个脚本会调用：

```text
POST /api/workflow/v8/subtitle-workflow/ai-generate
```

接口耗时较长时，脚本会定时向 stderr 输出等待秒数。只要没有报错，继续等待后端完成。

它等价于前端「AI生成字幕」按钮，会由 xycut 后端完成：

1. 根据最终成稿做语义字幕结构规划，避免过碎，也避免超长整段。
2. 选择 01 单行默认、02 单行强调、03 重点预设，并参考 `emphasis_ratio` 控制 03 的目标比例。
3. 为 01/02 生成关键词高亮范围；03 重点预设不做关键词或划重点。
4. 独立生成需要的英文副字幕。
5. 为 03 做语义拆分和主题选择；第三步只把单条 03 拆成 1-3 个 `segments`，不再继续拆成多条 03。超长内容应在第二步先拆短并重新判断 01/02/03。
6. 根据模板资产池自动匹配字幕个人预设和样式个人预设。
7. 写回 `short_subtitles.json` 和 `subtitle_layout_plan.json`。

脚本成功后返回：

```json
{
  "status": "success",
  "review_url": "http://127.0.0.1:23568/v8/<task_id>",
  "short_subtitle_count": 0,
  "layout_item_count": 0,
  "ai_call_count": 0
}
```

## B3. 手动写回方式：只用于调试

如果用户明确提供了 `agent_subtitle_plan.json`，或后端 AI 不可用但仍要手动写回，可以使用：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_agent_subtitle_plan.py <task_id或task_dir> "<task_dir>/agent/agent_subtitle_plan.json"
```

新版手动计划可以包含：

```json
{
  "enabled": true,
  "source": "agent_generated",
  "asset_workflow": true,
  "items": [
    {
      "index": 0,
      "source_indices": [0],
      "text": "听我一句劝",
      "style_id": "01",
      "parts": {"main": "听我一句劝"},
      "highlight_ranges": [{"field": "main", "start": 2, "end": 4, "text": "一句"}]
    },
    {
      "index": 1,
      "source_indices": [1],
      "text": "人均800玩转五天四夜",
      "style_id": "03",
      "parts": {"main": "人均800玩转五天四夜"},
      "segments": ["人均800", "玩转五天四夜"],
      "theme": "价格利益"
    }
  ]
}
```

注意：手动写回脚本只负责保存，不会替 Agent 做 AI 判断。真正生成草稿时，xycut 后端仍会按当前模板补算或修复资产匹配。

## B4. 字段说明

- `text`：完整中文字幕，必须存在。
- `style_id`：`01`、`02` 或 `03`。
- `parts`：建议至少写 `main`；如果已有英文可写 `main_en` 或 `text_2`。
- `highlight_ranges`：只用于 01/02 关键词高亮范围。关键词必须来自原字幕，不要整句高亮；03 不写 `highlight_ranges`、`highlights` 或 `parts.keyword`。
- `segments`：03 的分段，只用于匹配样式个人预设。必须按顺序拼回 `text`。
- `theme`：03 的 8 个主题之一：`重点突出`、`转折反差`、`疑问悬疑`、`提醒避坑`、`正向结果`、`惊讶冲击`、`轻松幽默`、`价格利益`。
- `asset_match`：可选。一般由后端匹配，不建议 Agent 手写。
- `effect_theme_id`、`sound_effect_id`：不作为当前字幕编排必填字段。

## B5. 返回用户

写回成功后，返回：

```text
http://127.0.0.1:23568/v8/<task_id>
```

告诉用户刷新或打开该页面，在右侧字幕编排中检查结果。确认后再由用户点击「生成草稿」。

