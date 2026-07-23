# Agent 字幕编排细则

这份规则用于约束 Codex/智能体如何生成小映模板字幕。核心原则是：Agent 负责 AI 判断，小映负责保存和执行。

## 不要做的事

- 不要调用 `/api/workflow/v8/subtitle-workflow/ai-generate`。
- 不要让小映内置 AI 拆字幕或选样式。
- 不要生成 SRT 来冒充模板字幕。
- 不要直接覆盖 `short_subtitles.json` 或 `subtitle_layout_plan.json`。
- 不要使用旧字段 `sound_effect_id`。
- 不要输出模板不支持的 parts。

## 字幕拆分

- 按语义拆短，不按字数硬切。
- 默认按 `final_copy.json` 的行顺序处理。
- 单条字幕建议 6-12 个字。
- 过长句按自然停顿拆，例如“但是、所以、如果、因为、就是、然后、第一、第二”。
- 不要把固定词、数字、单位、英文拆断。
- 不要丢字、重复、乱序。

## 样式选择

- 01/02 通常都是普通字幕，应按节奏混合使用。
- 03 是重点样式，只用于真正重点句。
- 有 A/B parts 的样式才拆 A/B。
- 没有 A/B 的样式只写 `main`。
- 句子太短时，优先选单字段样式，不要为了用 A/B 把短词拆碎。

## parts 规则

A/B 样式：

```json
{
  "text": "然后配上一个声音和字幕",
  "parts": {
    "part_a": "然后配上一个声音",
    "part_b": "和字幕"
  }
}
```

单字段样式：

```json
{
  "text": "就是一条视频了",
  "parts": {
    "main": "就是一条视频了"
  }
}
```

重点关键词样式：

```json
{
  "text": "还能低成本批量剪视频",
  "style_id": "03",
  "parts": {
    "main": "还能低成本批量剪视频",
    "keyword": "低成本"
  },
  "effect_theme_id": "emphasis_light"
}
```

## highlights

- 只高亮 parts 中真实存在的词。
- 通常 2-5 个字。
- 不要整句高亮。
- 不要高亮与原字幕一样长的词。

示例：

```json
{
  "highlights": {
    "main": ["低成本"]
  }
}
```

## keyword

- 只能是一个核心词。
- 通常 2-4 个字，最多 6 个字。
- 不能等于整条字幕。
- 只在模板支持 `keyword` 的样式中使用。

## effect_theme_id

- 必须来自 `static/template/effect_packs.json`。
- 01 通常不加效果。
- 02 少量加轻效果。
- 03 必须加效果。
- 不要为了凑数量大量加同一个效果。

## 保存

Agent 生成完成后，写入中间结果：

```text
<task_dir>/agent/agent_subtitle_plan.json
```

然后调用：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_agent_subtitle_plan.py <task_id> "<task_dir>/agent/agent_subtitle_plan.json"
```

保存脚本会同步写入小映需要的短字幕和编排计划。
