# 模式 C：素材协作

目标：基于xycut已审核成稿，协助生成或下载图片/视频素材，并通过xycut导入接口写回 `material_plan.json`。

收到用户给出的xycut任务目录后，默认只做分析，不要立刻生成图片，不要写入项目文件，不要调用导入 API。

## C1. 读取成稿

第一步优先读取：

```text
<task_dir>/final_copy.json
```

这个文件是权威成稿映射，里面的 `lines[].line_id` 是xycut原始行号。这个行号可能跳号，不一定是连续的。

可以辅助阅读：

```text
<task_dir>/final_copy.txt
```

`final_copy.txt` 只是人工审核后的纯文本，方便快速阅读文案。不要用它推断 `line_id`。

复制提示词时，xycut会根据源文件类型提前写明本次的素材匹配模式：

- `全部匹配`：来源是纯音频。默认每一行成稿都需要画面素材。
- `重点匹配`：来源是视频。默认已有原始画面，只给核心观点、转场、强调句、强画面感内容补充素材。

这个模式已经由xycut决定，Agent 不要再询问用户“全部匹配还是部分匹配”。如果用户后续主动要求改成另一种模式，再按用户的新要求执行。

## C2. 先给用户配图建议

读取后先完成：

1. 统计一共有多少行成稿。
2. 按提示词中的素材匹配模式，判断默认需要匹配多少个画面。
3. 给用户返回简洁的逐行配图建议，让用户确认。
4. 如果当前是 `全部匹配`，默认逐行建议画面；如果有些行不适合单独配图，可以建议合并或跳过，但不要擅自执行。
5. 如果当前是 `重点匹配`，只挑出建议配图的重点行，并说明为什么这些行需要画面。

如果用户根据建议想调整文案、换行、合并行或拆分行，必须提示用户回到xycut前端界面修改。xycut前端会自动保存最新成稿到：

```text
<task_dir>/final_copy.txt
```

用户修改完成后，需要让用户告诉 Agent“已修改，重新读取”。收到这类确认后，重新读取 `final_copy.txt`，不要使用旧的行数和旧的配图建议继续执行。重新读取时也必须同步读取 `final_copy.json`，以最新的 `lines[].line_id` 为准。

建议返回格式：

```text
已读取成稿：共 20 行。
素材匹配模式：全部匹配 / 重点匹配
建议生成：20 张画面 / 6 张重点画面

初步配图建议：
1. 第 1 行「文案摘录」 -> 画面方向：人物展示/产品特写/场景图/概念图
2. 第 5 行「文案摘录」 -> 画面方向：……

请确认：
- 素材尺寸是 9:16、1:1、16:9，还是其他？
- 素材风格使用什么？是否使用指定生图 skill、Pexels 或其他素材来源？
- 是否需要固定角色、固定 IP、品牌风格或模板风格？
- 是否先生成 1-3 张样张确认？
```

除非用户在提示词中已经明确要求“直接生成素材”“直接生成图片”“开始生成”或已经提供完整生成要求，否则不要进入生成阶段。

进入具体素材流程前，先看提示词里的 `material_source_mode` 或素材来源说明：

- `classified`：只执行 C3 已分类素材库。
- `unclassified`：只执行 C4 未分类素材库。
- `pexels`：不读本地索引，按商业图库检索/下载素材。
- `generated`：不读本地索引，按用户要求生成素材。

不要在同一次任务里混合读取多种素材索引，除非用户明确要求混合多种素材来源。

## C3. 使用已分类素材库

如果用户要使用xycut已分类素材库，或者提示词中给出了素材库索引路径，优先读取：

```text
<task_dir>/agent/material_library_index.json
```

没有这个文件时，先导出索引：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/export_material_library_index.py <task_id>
```

接口等价请求：

```text
POST http://127.0.0.1:23568/api/workflow/v8/agent-material-library/export
```

重要：

- 不要调用xycut内置素材 AI 匹配接口 `/api/workflow/v8/material-match`。
- `material_library_index.json` 只是给 Agent 看的轻量素材清单。
- Agent 自己根据文案、标签、文件名和用户要求判断应该选哪个素材。
- 选中已分类素材库里的素材时，在结果文件里写 `source_path`；xycut导入接口会自动复制到当前任务目录，并写入稳定的相对路径。
- 同一个 `source_path` 默认只能匹配一行；不要为了凑数量重复使用同一个素材。

已分类素材库结果示例：

```json
{
  "task_id": "0704160321",
  "source": "agent_library",
  "lines": [
    {
      "line_id": "line_0007",
      "asset_id": "library_0001",
      "type": "video",
      "source_path": "D:/素材库/潮汕/牛肉火锅.mp4",
      "prompt": "这一行提到牛肉火锅，选择餐饮近景素材",
      "status": "success"
    }
  ]
}
```

## C4. 使用未分类素材库

未分类素材库不使用 `material-cache.json`，而是使用素材目录下的：

```text
<material_dir>/material-analysis-cache.json
```

这个文件记录每个单独素材的轻量 Agent 分析结果。分类素材和未分类素材不要混用：

- 分类素材库：使用 `material-cache.json`，靠目录标签匹配。
- 未分类素材库：使用 `material-analysis-cache.json`，靠 Agent 画面分析匹配。

第一步先同步索引：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/sync_unclassified_material_index.py "<material_dir>"
```

如果返回里有 `pending_materials`，说明有新增或变化素材需要分析。Agent 需要逐个查看这些素材，并保存精简分析：

```json
{
  "summary": "一句话画面描述，尽量短，适合匹配文案",
  "keywords": ["关键词1", "关键词2", "关键词3"]
}
```

保存单个素材分析：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/save_unclassified_material_analysis.py "<material_dir>" "<material_id>" "<analysis_json或analysis文件路径>"
```

全部必要素材分析完成后，为当前 xycut 任务导出压缩匹配索引：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/export_unclassified_material_match_index.py <task_id> "<material_dir>"
```

导出文件位置：

```text
<task_dir>/agent/material_analysis_match_index.json
```

匹配索引会自动压缩字段：

```json
{
  "id": "m_xxx",
  "n": "文件名.mp4",
  "t": "v",
  "d": 12.5,
  "s": "一句话画面描述"
}
```

字段含义：

- `id`：素材 ID，最终返回这个。
- `n`：文件名。
- `t`：`v` 视频，`i` 图片。
- `d`：时长秒。
- `s`：画面描述。

如果素材数量超过 100，xycut 会按每行文案先做一次轻量初筛，输出 `line_candidates`；Agent 只需要在每行候选里选择最合适素材。

未分类素材结果示例：

```json
{
  "task_id": "0704160321",
  "source": "agent_unclassified",
  "material_dir": "D:/素材库/未分类旅游素材",
  "lines": [
    {
      "line_id": "line_0007",
      "material_id": "m_abc123456789",
      "prompt": "这一行讲潮汕美食，选择牛肉火锅画面",
      "status": "success"
    }
  ]
}
```

重要：

- Agent 最终只需要返回 `material_id`，不要返回完整素材路径。
- xycut 后端会用 `material_id` 从 `material-analysis-cache.json` 找到真实路径。
- 不要每次重建全部分析索引；新增素材只分析新增，删除素材会自动从索引移除。
- 同一个 `material_id` 默认只能匹配一行；如果素材数量不足必须复用，要在 `prompt` 里说明为什么复用。

## C5. 按用户要求生成素材

只有用户明确确认开始生成或开始下载素材后，才执行下面流程。

1. 按 `final_copy.json` 的 `lines` 逐行处理。
2. 每一行必须使用 `final_copy.json` 中原始的 `line_id`，不要按第 1 行、第 2 行自行生成连续编号。
3. 根据xycut提示词指定的素材匹配模式，以及用户确认后的具体行清单生成图片或视频素材。
4. 素材必须保存到当前xycut任务目录内部。

图片素材路径示例：

```text
<task_dir>/materials/<line_id>/agent_image_0001/source.png
```

Pexels 或其他视频素材路径示例：

```text
<task_dir>/materials/<line_id>/pexels_0001/source.mp4
```

同一行多张候选素材：

```text
<task_dir>/materials/<line_id>/agent_image_0002/source.png
```

生成规则：

- 不要把图片、视频、缓存或结果写进 `C:/Users/Administrator/.codex/skills/xycut-koubo-skill`。
- 不要直接修改 `material_plan.json`。
- 如果某一行生成失败，继续处理其他行，并在结果文件里记录失败原因。
- 支持分批生成。用户如果只要求先生成 2-3 张样张，生成完这一批就立刻写结果文件并调用xycut导入 API。
- 不要等全部图片都生成完才导入。
- xycut后端会合并写入 `material_plan.json`，不要覆盖已有素材。

## C6. 生图风格

如果用户明确指定其他生图 skill、图片风格、人物 IP、品牌风格或素材要求，优先按用户指定执行。

如果用户没有指定，先询问用户；用户要求直接继续时，默认使用：

- 竖屏 9:16
- 适合短视频口播画面
- 图片尺寸 1080x1920
- 可以结合可用的 `dayuan-ip` 或其他生图 skill 完成

## C7. 保存结果文件

图片或视频素材准备完成后，写入：

```text
<task_dir>/agent/v8_image_material_result.json
```

格式：

```json
{
  "task_id": "0704160321",
  "source": "agent_generated_material",
  "lines": [
    {
      "line_id": "line_0007",
      "asset_id": "agent_image_0001",
      "type": "image",
      "file_path": "materials/line_0007/agent_image_0001/source.png",
      "prompt": "本行实际使用的生图提示词",
      "status": "success"
    },
    {
      "line_id": "line_0014",
      "asset_id": "pexels_0001",
      "type": "video",
      "file_path": "materials/line_0014/pexels_0001/source.mp4",
      "thumb_path": "materials/line_0014/pexels_0001/thumb.jpg",
      "preview_path": "materials/line_0014/pexels_0001/preview.mp4",
      "prompt": "本行实际使用的检索词或素材说明",
      "status": "success"
    }
  ]
}
```

注意：

- `file_path` 必须是相对 `<task_dir>` 的路径。
- 如果素材来自已分类素材库，可以不写 `file_path`，改写绝对 `source_path`。
- 如果素材来自未分类素材库，可以不写 `file_path`，改写 `material_id`，并在顶层提供 `material_dir`。
- `type` 可以是 `image` 或 `video`；不填时xycut会按文件扩展名推断。
- `line_id` 必须来自 `final_copy.json` 的 `lines[].line_id`。
- 成功项必须保证素材文件真实存在。
- 英文路径分隔符建议统一使用 `/`。

## C8. 导入到xycut

结果文件写好后，调用xycut后端 API：

优先使用脚本：

```bash
python C:/Users/Administrator/.codex/skills/xycut-koubo-skill/scripts/import_material_result.py <task_id> "agent/v8_image_material_result.json"
```

第二个参数推荐传相对任务目录路径，避免绝对路径转义或 task_id 不一致导致导入失败。完整绝对路径也可以，但必须位于当前 `<task_dir>` 内。

接口等价请求：

```text
POST http://127.0.0.1:23568/api/workflow/v8/agent-image-materials/import
```

请求体：

```json
{
  "task_id": "<task_id>",
  "result_path": "agent/v8_image_material_result.json"
}
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:23568/api/workflow/v8/agent-image-materials/import" `
  -ContentType "application/json" `
  -Body (@{
    task_id = "<task_id>"
    result_path = "agent/v8_image_material_result.json"
  } | ConvertTo-Json -Depth 6)
```

导入成功后，把xycut页面链接返回给用户：

```text
http://127.0.0.1:23568/v8/<task_id>
```

用户刷新页面后，就能在「素材匹配」页看到 Agent 生成或下载的素材。
