# 模式 D：封面写回

目标：把已经生成好的封面图片接入xycut项目。封面图片的创意、构图、人物 IP、尺寸和生成方式，交给 `dayuan-ip` 或用户指定的其他生图 skill 处理；xycut-koubo-skill 不负责设计封面图，只负责把最终图片登记到xycut。

## D1. 先确认封面图已经生成

封面图必须先由其他生图 skill 或用户手动准备好，并保存到当前xycut任务目录内部，例如：

```text
<task_dir>/cover/agent_cover_001.png
```

不要把封面图保存到 `C:/Users/Administrator/.codex/skills/xycut-koubo-skill` 目录，也不要只返回外部 URL。xycut需要本地文件路径，刷新页面后才能稳定预览和生成草稿。

如果用户还没有生成封面图，需要先让对应的生图 skill 完成图片生成。常见默认建议：

- 竖屏 9:16
- 1080x1920
- 适合短视频封面
- 如果用户指定了固定 IP、品牌风格或封面文案，优先按用户指定

## D2. 写入xycut封面计划

封面图准备好后，运行：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_cover_workflow.py <task_id> "<task_dir>/cover/agent_cover_001.png"
```

也可以把第一个参数换成任务目录：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_cover_workflow.py "<task_dir>" "<task_dir>/cover/agent_cover_001.png"
```

脚本会写入：

```text
<task_dir>/cover_plan.json
```

写入内容包括：

- `enabled: true`
- `cover_path`: 相对任务目录的封面路径
- `file_path`: 同封面路径
- `source: agent_generated_cover`

## D2.5. 如果同时有封面标题

封面标题不是封面图片路径的一部分。不要只把标题写进 `cover_plan.json` 的 `title` 字段，否则xycut前端标题文本框可能不会展示。

如果本次也生成了封面标题，必须同时运行标题写回脚本：

方式一：写封面时直接带标题：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_cover_workflow.py <task_id> "<task_dir>/cover/agent_cover_001.png" --title "第一行标题
第二行标题"
```

方式二：封面和标题分开写：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_title_workflow.py <task_id> "第一行标题
第二行标题"
```

也可以先把标题保存为文本文件，再传入文件路径：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_title_workflow.py <task_id> "<task_dir>/agent/newstitle.txt"
```

脚本会写入：

```text
<task_dir>/review_state.json -> jianying_settings.newstitle_content
```

用户刷新xycut后，标题文本会显示在「草稿生成」页的标题文本框中。

## D3. 返回给用户

写入成功后，把xycut页面链接返回给用户：

```text
http://127.0.0.1:23568/v8/<task_id>
```

用户刷新页面后，可以在「草稿生成」页的封面模块看到封面预览。后续点击生成草稿时，xycut会自动启用该封面。

## D4. 禁止事项

- 不要直接修改剪映草稿 JSON。
- 不要直接修改 `draft_content.json`。
- 不要把封面图写到 skill 目录。
- 不要把任务目录外的图片路径写入 `cover_plan.json`。
- 不要在本模式里强行决定封面风格；封面风格由用户或专门的生图 skill 决定。
