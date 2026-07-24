# 模式 B：Agent 字幕编排

目标：让 Codex/智能体使用自己的理解能力完成短字幕和模板编排；xycut只负责保存、页面展示和后续生成剪映草稿。

## 核心边界

- Agent 是字幕编排的大脑。
- xycut是保存器、编辑器和草稿生成器。
- 不调用xycut内置 AI 字幕生成接口。
- 不生成 SRT 来代替xycut模板字幕。
- 不直接覆盖任务 JSON 文件，必须通过保存脚本/API 写回。

xycut页面右侧字幕列读取：

```text
<task_dir>/short_subtitles.json
<task_dir>/subtitle_layout_plan.json
```

## B1. 任务前检查

先确认任务目录或 `task_id` 有效，并读取：

```text
<task_dir>/final_copy.json
<task_dir>/final_copy.txt
<task_dir>/review_state.json
```

如果没有 `final_copy.json/final_copy.txt`，不要生成字幕编排。告诉用户先完成「口播剪辑」审核并保存成稿。

如果已经存在用户手动编辑过的：

```text
<task_dir>/subtitle_layout_plan.json
```

并且 `source` 类似 `user_edited`，不要覆盖，除非用户明确要求重新生成。

## B2. 读取 Agent 上下文

不要直接读取 xycut 项目源码、模板 JSON 或加密效果库。模板和效果库可能被打包或加密，Agent 只读取 xycut 后端导出的精简上下文。

优先调用：

```text
GET http://127.0.0.1:23568/api/workflow/v8/agent-context/<task_id>
```

也可以用脚本包装这个接口：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/export_subtitle_template_specs.py "<task_id或task_dir>"
```

如果接口或脚本返回失败，停止处理并告诉用户 xycut 后端没有提供完整上下文。不要在缺少模板字段或特效 ID 的情况下硬生成字幕。

上下文决定：

- 哪些 `style_id` 可用。
- 每个样式必须写入哪些 `parts` 字段，权威来源是 `template.styles[].chinese_sources / english_sources / keyword_sources`。
- 每个样式需要哪些中文字段，例如 `part_a/part_b/main/text/keyword`。
- 每个样式是否需要英文副字幕字段，例如 `main_en/text_2/text_2_left/text_2_right/left_en/right_en`。
- 01/02/03 的 A 档最大字数。
- 03 是否有 `keyword_variants`。
- 可用的 `effect_theme_id`，来自 `effect_themes.themes[].id`。
- 最终成稿，来自 `final_copy.lines[]`。

先检查上下文：

```text
status 必须是 success
final_copy.available 必须是 true
template.styles 必须非空
如果 template.has_keyword_style=true，effect_themes.available 应该是 true
```

注意：不要照抄历史模板示例字段。实际字段只看当前上下文。

## B3. Agent 自行生成字幕编排

Agent 按三步思路在自己脑中完成，但最终只保存一个结果文件。

### 第一步：拆短字幕

从最终成稿拆成适合竖屏显示的短字幕：

- 按语义拆，不按字数硬切。
- 默认不要合并多条原文。
- 单条建议 6-12 个字，尽量不要超过模板 A 档上限。
- 不丢字，不乱序，不重复。
- 可以修正极明显 ASR 错字，但不要润色、扩写、总结。

### 第二步：选择样式和 parts

根据模板选择 `style_id`：

- 01/02 通常都是普通字幕，按节奏混合使用。
- 当前样式的 `layers[].source` 里有 `part_a/part_b` 才拆 A/B；没有 A/B 时按模板 source 写 `text` 或 `main`。
- A/B 必须能自然拼回完整 `text`，不要把固定词、数字、单位、英文拆断。
- 如果一句话太短，不适合 A/B，就优先选单字段样式。
- 03 只给真正重点句使用，并按模板中文 source 保留完整字幕。
- 03 不按比例硬凑：20 条以内 0-2 条，20-40 条 2-4 条，40-80 条 4-6 条，80 条以上 5-8 条。优先给开头钩子、强利益点、价格数字、反转结论、行动号召。
- 生成 `parts` 时只能写当前 `style_id` 在上下文里列出的 `chinese_sources / english_sources / keyword_sources` 字段；不要因为 `role` 叫 `left_cn/right_cn` 就把字段写成 `left_cn/right_cn`。
- 不要额外写兼容字段。比如当前 03 只有 `chinese_sources=["text"]`、`keyword_sources=["keyword"]`，就只能写 `parts.text` 和 `parts.keyword`，不要再写 `main/part_a/part_b`。

### 第三步：增强

按需要补充：

- `highlights`：只选择 parts 中真实存在的短词，通常 2-5 个字，不要整句高亮。
- `keyword`：只在模板支持 `keyword` 的样式里使用，通常 2-4 个字，不能等于整条字幕。
- `effect_theme_id`：必须来自上下文里的 `effect_themes.themes[].id`；不要为了凑数量大量加音效。
- 03 必须写 `keyword` 和 `effect_theme_id`。如果拿不到效果主题，停止并提示上下文不完整，不要因为读不到完整模板/效果库就直接放弃 03。
- 英文副字幕：如果模板 `layers[].source` 里包含英文字段，必须同步写入简短自然的英文，不要留到生成草稿时再由 xycut 内置 AI 补齐。

## B4. Agent 输出文件

建议先把结果保存为：

```text
<task_dir>/agent/agent_subtitle_plan.json
```

格式：

```json
{
  "enabled": true,
  "source": "agent_generated",
  "items": [
    {
      "index": 0,
      "source_indices": [0],
      "text": "然后配上一个声音",
      "style_id": "02",
      "parts": {
        "main": "然后配上一个声音"
      },
      "highlights": {
        "main": ["声音"]
      }
    },
    {
      "index": 1,
      "source_indices": [0],
      "text": "就是一条视频了",
      "style_id": "01",
      "parts": {
        "part_a": "就是一条",
        "part_b": "视频了",
        "text_2_left": "That makes",
        "text_2_right": "one video"
      }
    }
  ]
}
```

关键要求：

- `items[].text` 是该条完整中文字幕。
- `parts` 必须且只能包含当前 `style_id` 的上下文 sources 字段。
- `role` 只用于理解语义，不是写入字段；写入字段只看上下文 sources。
- `part_a + part_b` 必须等于 `text`。
- 单字段样式如果上下文 source 是 `text`，就只写 `parts.text`；如果上下文 source 是 `main`，就只写 `parts.main`。
- 如果模板支持英文副字幕 source，必须输出对应英文；A/B 样式常见是 `text_2_left/text_2_right`，单字段样式常见是 `main_en` 或 `text_2`。
- 英文也只写上下文 sources 中列出的字段；不要额外补写 `left_en/right_en/text_2` 等兼容字段。
- 英文要短、自然、适合画面点缀，不要逐字硬翻译，不要修改中文。
- 不要输出旧字段 `sound_effect_id`。

## B5. 写回xycut

生成 `agent_subtitle_plan.json` 后，调用：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_agent_subtitle_plan.py <task_id> "<task_dir>/agent/agent_subtitle_plan.json"
```

也可以传任务目录：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_agent_subtitle_plan.py "<task_dir>" "<task_dir>/agent/agent_subtitle_plan.json"
```

脚本只调用xycut保存 API：

```text
POST /api/workflow/v8/short-subtitles/save
POST /api/workflow/v8/subtitle-layout-plan/save
```

它不会调用xycut内置 AI。

## B6. 返回用户

写回成功后，返回：

```text
http://127.0.0.1:23568/v8/<task_id>
```

告诉用户刷新或打开该页面，在右侧字幕编排中检查 Agent 生成的结果。
