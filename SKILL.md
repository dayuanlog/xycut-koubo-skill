---
name: xycut-koubo-skill
description: "使用 xycut 处理口播剪辑工作流。它负责调用 xycut 的脚本和接口，把 Agent 结果稳定写回 xycut 任务目录，并返回 xycut 任务页面链接。"
---

# xycut Koubo Skill

这个 skill 服务 xycut Koubo 流程。xycut 后端负责转写、时间线、审核台、结果保存、页面展示和剪映草稿生成；Agent 负责判断用户意图、完成 AI 字幕编排、素材/封面协作，并通过项目接口把结果写回 xycut 任务目录。

## 总原则

1. 任务产物必须写到当前 xycut 任务目录，通常是 `<task_dir>/...`。
2. 不要把图片、视频、JSON 结果、缓存写到 `C:/Users/Administrator/.codex/skills/xycut-koubo-skill` 目录。
3. 不要直接修改 `data/config.json`、剪映 `draft_content.json` 或用户手动选择过的完整计划文件。
4. 能用脚本写回就用脚本写回，不要手动拼大段 JSON 覆盖用户数据。
5. 只要完成了 xycut 写回，都返回 `http://127.0.0.1:23568/v8/<task_id>`。
6. 不确定是否删除口播内容时，保留给 xycut 审核台人工确认。
7. `final_copy.json` 是成稿与原始 `line_id` 的权威映射；`final_copy.txt` 只适合快速阅读文案。
8. xycut 字幕编排不是 SRT。右侧字幕列只读取 `short_subtitles.json` 和 `subtitle_layout_plan.json`。
9. 字幕编排默认由 Agent 使用自身 AI 能力完成；xycut 只负责导出精简上下文、保存、展示和生成草稿。
10. xycut 模板字幕字段由后端维护：03 重点样式保留完整字幕并补充 `keyword`，01/02/03 可补充 `highlights`，02/03 的音效/文字动画主题使用 `effect_theme_id`，不要再使用旧的 `sound_effect_id`。
11. 如果当前模板包含英文副字幕字段，例如 `main_en`、`left_en`、`right_en`、`text_2`、`text_2_left`、`text_2_right`，Agent 生成字幕编排时必须一起写入英文内容，不要留给 xycut 内置 AI 补齐。
12. 生成 `parts` 时必须以当前模板中对应 `style_id` 的 `layers[].source` 为准，不要按 `01/02/03` 或 `role/name` 猜字段；`role` 只适合理解显示语义，真正写入字段看 `source`。
13. 不要读取 xycut 项目源码、不要解密模板、不要直接读取完整模板 JSON；需要模板、特效、任务文案时，只调用 xycut Agent 上下文接口或对应导出脚本。
14. `parts` 只能写 Agent 上下文里当前 `style_id` 的 `chinese_sources / english_sources / keyword_sources` 字段；不要额外写 `main/text/part_a/part_b` 等兼容字段。

## 入口判断

先判断用户到底要做哪类 xycut 工作，再读取对应 reference。不要一次性读完所有参考文件。

| 用户意图 | 模式 | 必读 reference | 主要产物 |
| --- | --- | --- | --- |
| 音视频路径、转写、剪口播、预审口误/重复/错字 | 模式 A：Agent 自动预审 | `references/auto_review.md` | `review_state.json`、`final_copy.json`、`final_copy.txt` |
| 短字幕、字幕编排、AI生成并编排、右侧字幕列、xycut 模板字幕 | 模式 B：Agent 字幕编排 | `references/subtitle_workflow.md`、需要时读 `references/subtitle_rules.md` | `short_subtitles.json`、`subtitle_layout_plan.json` |
| 配图、素材、逐行画面、生图、Pexels、导入素材 | 模式 C：素材协作 | `references/material_workflow.md` | `materials/...`、`agent/v8_image_material_result.json`、`material_plan.json` |
| 封面、导入封面、写入封面、封面图片已生成 | 模式 D：封面写回 | `references/cover_workflow.md` | `cover/...`、`cover_plan.json` |
| 草稿准备、生成标题、短字幕+标题+封面、生成草稿前准备 | 模式 E：草稿准备协作 | `references/draft_prepare_workflow.md` | 字幕编排、标题文本、封面计划 |
| SRT、外挂字幕、字幕文件、给导出视频挂字幕 | 不是模式 B | 按用户需求另行处理 | `.srt`，但不会让 xycut 右侧字幕列展示 |

### 快速路由

- 用户消息里是一个或多个音视频文件路径：进入模式 A。
- 用户消息里是 xycut 任务目录，并要求口播剪辑审核、继续分析逐字稿、预审口误/重复/错字：进入模式 A，但不要重新转写。
- 用户消息里是 xycut 任务目录，并要求“短字幕”“字幕编排”“AI生成并编排”：进入模式 B。
- 用户消息里是 xycut 任务目录，或者包含 `final_copy.json/final_copy.txt`，并要求配图/素材：进入模式 C。
- 用户消息里是 xycut 任务目录，并要求导入封面、写入封面、使用已生成封面图：进入模式 D。
- 用户消息里是 xycut 任务目录，并要求草稿准备、标题、封面、字幕一起处理：进入模式 E。
- 用户只要求打开或继续某个任务：返回或打开 `http://127.0.0.1:23568/v8/<task_id>`。

## 常用脚本

| 场景 | 脚本 |
| --- | --- |
| 创建 xycut 转写任务 | `scripts/transcribe.py` |
| 准备口播预审分块 | `scripts/prepare_analysis.py` |
| 可选规则预选 | `scripts/rule_prefill.py` |
| 合并预审结果 | `scripts/merge_analysis.py` |
| 保存自动预审结果 | `scripts/save_auto_review.py` |
| 保存 Agent 字幕编排 | `scripts/save_agent_subtitle_plan.py` |
| 导出当前模板字幕字段表 | `scripts/export_subtitle_template_specs.py` |
| 导出已分类素材库索引 | `scripts/export_material_library_index.py` |
| 同步未分类素材索引 | `scripts/sync_unclassified_material_index.py` |
| 保存未分类素材分析 | `scripts/save_unclassified_material_analysis.py` |
| 导出未分类素材匹配索引 | `scripts/export_unclassified_material_match_index.py` |
| 导入 Agent 素材结果 | `scripts/import_material_result.py` |
| 追加单个素材 | `scripts/append_material_asset.py` |
| 写回标题文本 | `scripts/save_title_workflow.py` |
| 写回已生成封面 | `scripts/save_cover_workflow.py` |

## 关键禁止项

- 不要把“字幕编排”做成 SRT 文件。
- 不要调用 xycut 内置字幕 AI 接口；字幕理解、拆分、样式选择和增强由 Agent 完成。
- 不要调用 xycut 内置素材 AI 匹配接口 `/api/workflow/v8/material-match`；素材理解和选择由 Agent 完成，只通过导出索引和导入素材结果接口与 xycut 交换数据。
- 不要每次重新分析全部未分类素材；必须优先复用素材目录下的 `material-analysis-cache.json`，只补新增/变化素材。
- 匹配已有视频/图片素材时，同一个素材默认只能使用一次；除非用户明确要求复用，或可用素材明显不足并写明原因。
- 不要用 `final_copy.txt` 推断 `line_id`。
- 不要自己按第 1 行、第 2 行编造素材 `line_id`。
- 不要直接编辑 `material_plan.json`；素材协作结果应通过 xycut 导入 API 合并。
- 不要把任务目录外的图片路径写入 `cover_plan.json`。
- 不要覆盖用户已经手动替换或选择过的素材。

## 参考文件说明

- `references/auto_review.md`：音视频路径进入 xycut、Agent 自动预审、写回审核状态。
- `references/subtitle_workflow.md`：Agent 自行生成短字幕和模板编排，再通过 xycut 保存接口同步到右侧字幕列。
- `references/material_workflow.md`：根据已审核成稿做逐行素材协作，支持图片/视频/Pexels/分批导入。
- `references/cover_workflow.md`：把其他生图 skill 已生成的封面图写回 xycut。
- `references/draft_prepare_workflow.md`：生成草稿前的字幕、标题、封面协作总入口。
- `references/task_files.md`：任务目录和关键文件说明。
- `references/api_payloads.md`：接口 payload 示例。
- `references/subtitle_rules.md`：xycut 模板字幕编排细则。
