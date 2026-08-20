# 模式 E：草稿准备协作

目标：在用户点击 xycut「生成草稿」之前，协助补齐短字幕编排、标题文本和封面。最终剪映草稿仍由 xycut 后端生成，Agent 不直接修改剪映草稿 JSON。

## E1. 先检查当前任务状态

读取任务目录：

```text
<task_dir>
```

优先检查：

- `final_copy.json` / `final_copy.txt`：成稿是否已经存在。
- `short_subtitles.json` 和 `subtitle_layout_plan.json`：是否已有短字幕和模板编排。
- `review_state.json`：是否已有 `jianying_settings.newstitle_content`。
- `cover_plan.json`：是否已有封面。

先把缺失项告诉用户，并给出处理方案。不要一上来直接生成所有内容。

## E2. 短字幕和模板编排

如果缺少短字幕或字幕编排，按 `references/subtitle_workflow.md` 执行。新版默认调用后端当前 V8 AI 工作流：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/run_subtitle_workflow.py <task_id或task_dir>
```

这一步会生成并写回：

```text
short_subtitles.json
subtitle_layout_plan.json
```

不要生成 SRT 来代替 xycut 字幕编排。

只有在用户明确提供计划或后端 AI 不可用时，才使用手动保存脚本：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_agent_subtitle_plan.py <task_id> "<task_dir>/agent/agent_subtitle_plan.json"
```

## E3. 标题文本

标题文本来自已审核成稿，通常用于 xycut 模板标题层。Agent 可以先给出 1-3 行标题建议，让用户确认。

用户确认后，把标题写回。PowerShell 下推荐先把标题保存成 txt，再传文件路径：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_title_workflow.py <task_id> "<task_dir>/agent/newstitle.txt"
```

也可以直接传单行标题：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_title_workflow.py <task_id> "标题文本"
```

脚本会写入 `review_state.json -> jianying_settings.newstitle_content`。用户刷新 xycut 后，可以在「草稿生成」页看到标题文本。

## E4. 封面协作

封面图由 `dayuan-ip` 或用户指定的生图 skill 生成。xycut-koubo-skill 只负责写回已经生成好的封面图。

封面图保存到任务目录内部后，按 `references/cover_workflow.md` 执行：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_cover_workflow.py <task_id> "<task_dir>/cover/agent_cover_001.png"
```

## E5. 返回用户

完成任一写回后，都返回：

```text
http://127.0.0.1:23568/v8/<task_id>
```

告诉用户刷新页面检查「草稿生成」页。确认字幕、标题、封面都没问题后，再由用户在 xycut 页面点击「生成草稿」。

## 禁止事项

- 不要直接生成剪映草稿。
- 不要直接修改 `draft_content.json`。
- 不要把 SRT 当作 xycut 短字幕编排。
- 字幕编排按 `references/subtitle_workflow.md` 调用 xycut V8 后端。
- 不要把封面图片保存到 skill 目录。
- 不要覆盖用户已经人工修改过的字幕编排，除非用户明确要求重新生成。
