# 模式 B：Agent 字幕编排

目标：让 Codex/智能体使用自己的理解能力完成短字幕和模板编排；小映只负责保存、页面展示和后续生成剪映草稿。

## 核心边界

- Agent 是字幕编排的大脑。
- 小映是保存器、编辑器和草稿生成器。
- 不调用小映内置 AI 字幕生成接口。
- 不生成 SRT 来代替小映模板字幕。
- 不直接覆盖任务 JSON 文件，必须通过保存脚本/API 写回。

小映页面右侧字幕列读取：

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

## B2. 读取模板和效果库

优先从 `review_state.json` 读取当前模板：

```text
koubo_template_id
v8_template_id
```

如果没有选择记录，读取小映默认模板：

```text
static/template/index.json -> default_template_id
static/template/<template_id>/template.json
```

还需要读取：

```text
static/template/effect_packs.json
```

模板决定：

- 哪些 `style_id` 可用。
- 每个样式需要哪些中文 parts，例如 `part_a/part_b/main/keyword`。
- 01/02/03 的 A 档最大字数。
- 03 是否有 `keyword_variants`。
- 可用的 `effect_theme_id`。

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
- 有 `part_a/part_b` 的样式才拆 A/B；没有 A/B 的样式只写 `main`。
- A/B 必须能自然拼回完整 `text`，不要把固定词、数字、单位、英文拆断。
- 如果一句话太短，不适合 A/B，就优先选单字段样式。
- 03 只给真正重点句使用，并保留完整字幕 `main`。

### 第三步：增强

按需要补充：

- `highlights`：只选择 parts 中真实存在的短词，通常 2-5 个字，不要整句高亮。
- `keyword`：只在模板支持 `keyword` 的样式里使用，通常 2-4 个字，不能等于整条字幕。
- `effect_theme_id`：必须来自 `effect_packs.json`；不要为了凑数量大量加音效。

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
        "part_b": "视频了"
      }
    }
  ]
}
```

关键要求：

- `items[].text` 是该条完整中文字幕。
- `parts` 必须来自模板支持的字段。
- `part_a + part_b` 必须等于 `text`。
- 单字段样式的 `main` 必须等于 `text`。
- 不要输出英文 parts，除非用户明确要求双语模板字幕。
- 不要输出旧字段 `sound_effect_id`。

## B5. 写回小映

生成 `agent_subtitle_plan.json` 后，调用：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_agent_subtitle_plan.py <task_id> "<task_dir>/agent/agent_subtitle_plan.json"
```

也可以传任务目录：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_agent_subtitle_plan.py "<task_dir>" "<task_dir>/agent/agent_subtitle_plan.json"
```

脚本只调用小映保存 API：

```text
POST /api/workflow/v8/short-subtitles/save
POST /api/workflow/v8/subtitle-layout-plan/save
```

它不会调用小映内置 AI。

## B6. 返回用户

写回成功后，返回：

```text
http://127.0.0.1:23568/v8/<task_id>
```

告诉用户刷新或打开该页面，在右侧字幕编排中检查 Agent 生成的结果。
