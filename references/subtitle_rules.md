# Agent 字幕编排细则

这份规则用于约束 Codex/智能体如何生成xycut模板字幕。核心原则是：Agent 负责 AI 判断，xycut负责保存和执行。

## 不要做的事

- 不要调用 `/api/workflow/v8/subtitle-workflow/ai-generate`。
- 不要让xycut内置 AI 拆字幕或选样式。
- 不要生成 SRT 来冒充模板字幕。
- 不要直接覆盖 `short_subtitles.json` 或 `subtitle_layout_plan.json`。
- 不要使用旧字段 `sound_effect_id`。
- 不要输出模板不支持的 parts。
- 不要漏掉模板已经支持的英文副字幕 parts。
- 不要按样式 ID 猜字段；`01/02/03` 只是样式编号，真正字段必须读取当前模板 `layers[].source`。

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

### source 优先

生成任何字幕前，先读取 xycut Agent 上下文接口返回的当前模板样式：

```text
template.styles[].chinese_sources
template.styles[].english_sources
template.styles[].keyword_sources
```

这些 `sources` 是 `parts` 写入字段的唯一权威。`source_roles`、`name`、样式中文名只用于理解显示位置和语义。

`parts` 必须且只能写当前 `style_id` 的 sources 字段：

```text
allowed_parts = chinese_sources + english_sources + keyword_sources
```

不要额外写兼容字段。比如当前样式只有 `chinese_sources=["text"]`、`keyword_sources=["keyword"]`，就只能写 `parts.text` 和 `parts.keyword`。

示例：

```json
{
  "role": "right_en",
  "source": "text_2_right"
}
```

这表示必须写：

```json
{
  "parts": {
    "text_2_right": "one video"
  }
}
```

不能只写：

```json
{
  "parts": {
    "right_en": "one video"
  }
}
```

只有当上下文的 `english_sources` 同时列出 `text_2_right` 和 `right_en` 时，才可以两个都写；否则只写列出的那个。

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
    "text": "还能低成本批量剪视频",
    "keyword": "低成本"
  },
  "effect_theme_id": "emphasis_light"
}
```

英文副字幕样式：

如果模板 `layers[].source` 中包含英文副字幕字段，必须一起输出：

```json
{
  "text": "然后配上一个声音和字幕",
  "style_id": "01",
  "parts": {
    "part_a": "然后配上一个声音",
    "part_b": "和字幕",
    "text_2_left": "Add a voice",
    "text_2_right": "and subtitles"
  }
}
```

常见 source 对应关系：

- A/B 中文：通常是 `part_a/part_b`，但必须以模板 source 为准。
- 单字段中文：可能是 `text` 或 `main`，必须以模板 source 为准，只写当前 source。
- A/B 英文：可能是 `text_2_left/text_2_right`，也可能是 `left_en/right_en`。
- 单字段英文：可能是 `main_en` 或 `text_2`。
- 不要额外补写兼容英文。只有上下文 sources 中出现的英文字段才写。

英文规则：

- 英文要短、自然，适合画面点缀。
- 不要逐字硬翻译，不要改动中文。
- 不要把英文写进中文字段。
- 模板没有英文字段时，不要额外编造英文字段。

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

- 必须来自 xycut Agent 上下文里的 `effect_themes.themes[].id`。
- 不要直接读取 `static/template/effect_packs.json`，效果库可能已加密为 `.json.enc`。
- 01 通常不加效果。
- 02 少量加轻效果。
- 03 必须加效果。
- 不要为了凑数量大量加同一个效果。
- 03 不按比例硬凑，按总字幕数量自然控制：20 条以内 0-2 条，20-40 条 2-4 条，40-80 条 4-6 条，80 条以上 5-8 条。
- 优先选择钩子、强利益点、价格、避坑、反转结论、行动号召；不要给普通过渡句。

## 保存

Agent 生成完成后，写入中间结果：

```text
<task_dir>/agent/agent_subtitle_plan.json
```

然后调用：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_agent_subtitle_plan.py <task_id> "<task_dir>/agent/agent_subtitle_plan.json"
```

保存脚本会同步写入xycut需要的短字幕和编排计划。
