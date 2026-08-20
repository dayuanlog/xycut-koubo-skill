# xycut-koubo-skill 开发排查记录

> 记录发现的问题和对应优化，方便后续排查。

## 2026-08-20

1. 问题：`save_title_workflow.py` / `save_cover_workflow.py` 在 skill 目录直接运行时可能找不到 `core`。
   优化：脚本会从环境变量、任务目录 `task_config.json.app_dir`、当前工作目录及父目录自动定位小映 APP 目录。

2. 问题：标题/封面脚本新增任务目录解析后，`main()` 首次 `_load_storage()` 仍未传入任务参数，可能绕过 `task_config.json.app_dir`。
   优化：`main()` 已改为 `_load_storage(args.task)`。

3. 问题：`run_subtitle_workflow.py` 只传 `task_id` 时返回的 `task_dir` 为空，不方便后续校验文件。
   优化：脚本会尝试通过 `/api/workflow/v8/agent-context/<task_id>` 补全 `task_dir`。

4. 问题：`rule_prefill.py` 的规则预选可能产生误删候选，文档示例容易让 Agent 机械合并。
   优化：文档已明确 `rule_prefill.json` 只是候选，必须复核后才参与合并。

5. 问题：素材协作中，“先给建议再确认”和“用户明确要求直接匹配”的边界不够清楚。
   优化：文档已明确用户说“直接匹配 / 完成匹配 / 导入素材 / 使用某分类素材匹配”时，可以直接执行并导入。

6. 问题：已分类素材库导出内容过长，Agent 需要二次筛选。
   优化：`export_material_library_index.py` 已新增 `--tag/--tags`、`--query`、`--compact`、`--top-per-tag`。

7. 问题：素材索引文档示例把素材库名称当成素材标签使用，容易筛不出结果。
   优化：文档已说明 `--tag/--tags` 是素材条目标签；选择素材库使用 `--material-path-index`。

8. 问题：PowerShell 命令行直接传多行标题容易转义失败。
   优化：文档已推荐把标题保存到 `<task_dir>/agent/newstitle.txt`，再传文件路径。

9. 问题：skill 开发测试问题没有固定记录位置。
   优化：`SKILL.md` 已说明开发测试问题可记录到 `DEV_NOTES.md`，普通任务产物仍不得写入 skill 目录。

10. 问题：封面尺寸口径仍需产品侧确认，例如小红书 3:4、视频封面 9:16、横版封面是否裁切或适配。
    优化：暂未写死规则；按用户当前明确要求执行，后续确认小映 APP 适配策略后再补文档。

11. 问题：`rule_prefill.py` 在任务 `0820151928` 中把 `word_129`（“对于”的“对”）预选为句首填充词；如果 Agent 机械合并会把“对于剩下99...”破坏成病句。
    优化：`rule_prefill.py` 已在命中“对”时检查后续是否为“于”，避免误删“对于”。

12. 问题：分块 `.json` 包含完整字级时间戳，直接读取时输出非常长；本次只需要核对少量 idx 和文本，容易超出上下文并截断。
    优化：已新增 `scripts/print_chunk_words.py`，支持按 idx 范围或句子 index 快速查看 `idx,text,start,end`。

13. 问题：模式 C 文档说明了 `material_source_mode=pexels`，但 skill 目录没有专用脚本封装“读取 final_copy -> 逐行生成 Pexels query -> 下载到 materials -> 写 v8_image_material_result.json -> 导入”的完整流程；本次只能在任务目录临时写 `agent/pexels_match_all.py` 调用 APP 的 `utils/pexels_downloader.py`。
    优化建议：新增 `scripts/run_pexels_material_workflow.py`，统一处理 API key 读取、逐行 query 映射、去重、缩略图生成、失败重试和导入。

14. 问题：当前任务 `0820151928` 的 `task_config.json` 和 APP 全局 `data/config.json` 中 Pexels `api_key` 都为空，但历史任务配置曾保留 key；Agent 在开发测试时不容易判断应该从哪里安全读取 key。
    优化建议：转写任务快照应明确记录 Pexels key 是否可用，或提供只返回“是否配置/从何处读取”的后端接口，避免 Agent 扫描历史任务配置。

15. 问题：`run_subtitle_workflow.py` 调用 `/subtitle-workflow/ai-generate` 时长时间没有任何进度输出；本次任务 `0820151928` 等待数分钟后才成功返回，期间 Agent 难以判断是 AI 编排正常耗时还是后端卡住。
    优化：`run_subtitle_workflow.py` 已在等待期间定时向 stderr 输出 elapsed time。

16. 问题：`save_cover_workflow.py` 用 `task_id` 直接调用时仍可能无法定位小映 APP 目录；本次任务 `0820151928` 需要手动设置 `XYCUT_APP_DIR` 并改传任务目录才成功。
    优化：`save_title_workflow.py` / `save_cover_workflow.py` 已在只有 `task_id` 时尝试通过 `/api/workflow/v8/agent-context/<task_id>` 补全任务目录。

17. 问题：`/api/workflow/v8/agent-context` 返回的 `rules` 曾包含过期字幕编排描述，可能和当前 skill 规则冲突。
    优化：已更新 `core/v8/X00_api.py` 中的 `agent-context` rules，仅保留当前接口边界。
