# MCGS MCP Editor Skill

[![CI](https://github.com/Babel36acl/mcgs-mcp-editor-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/Babel36acl/mcgs-mcp-editor-skill/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab.svg)](https://www.python.org/)

**非官方** MCGS Pro 工程文件（`.MCP`）解析/编辑技能与命令行工具：在**工程副本**上改标签、数值输入框、标准按钮和受限 BASIC 条件脚本，并把"文件回读成功"和"宿主验收通过"严格分开报告。

> **术语警告：这里的 MCP 不是 Model Context Protocol。** MCGS 的 `.MCP` 是 Access（Jet/MDB）格式的 HMI 组态工程文件，内部再套 CArchive/MFC 序列化的窗口记录。本项目与 Anthropic 的 MCP 协议无关。
>
> 这是**非官方社区工具**。MCGS / 昆仑通态相关产品与商标归各自权利人所有；厂商程序不受本仓库 GPL 许可约束。本仓库不包含厂商 EXE/DLL、安装包、真实工程或用户截图。

**English (short):** An unofficial Codex/agent skill plus Python tools for inspecting and patching MCGS Pro `.MCP` (Microsoft Access) HMI project copies — label text, numeric input binding/ranges, standard-button event scripts — with explicit, fail-closed evidence gates. Not the Model Context Protocol. Verified against McgsPro 3.5.1.7267 only.

---

## 目录

- [它解决什么问题](#它解决什么问题)
- [30 秒判断是否适用](#30-秒判断是否适用)
- [能力矩阵](#能力矩阵)
- [快速开始](#快速开始)
- [安装为 Agent 技能](#安装为-agent-技能)
- [仓库结构](#仓库结构)
- [命令行参考](#命令行参考)
- [编辑清单格式](#编辑清单格式)
- [证据分级：什么叫"验证过"](#证据分级什么叫验证过)
- [兼容性与版本锁定](#兼容性与版本锁定)
- [安全边界与发布范围](#安全边界与发布范围)
- [开发与测试](#开发与测试)
- [常见问题](#常见问题)
- [许可与商标](#许可与商标)
- [文档索引](#文档索引)

## 它解决什么问题

MCGS Pro 的工程是 Access 数据库，窗口内容又是 MFC `CArchive` 序列化的私有二进制。改动控件不能只靠"数据库能读出来"，因为宿主会校验嵌套长度、绑定对象 ID、编译数组和尾部数据；漏更新一层长度就会被判为"工程已损坏"。

本仓库提供三件事：

1. **定界读取**：按文档头、记录数、`u32 kind + u16 长度` 记录帧和 trailer 逐窗解析，解析失败单独报告，绝不把异常吞成"0 个控件"。
2. **带原像的写入**：每个编辑都要求原始 payload 的 SHA-256、字段偏移、预期旧值，并显式列出所有覆盖该变长字段的嵌套 `u16` 计数。写入走新文件，回读所有非系统表确认只有声明过的 BLOB 变化。
3. **能力门禁**：类型注册表 + 逐类放行 + 样本指纹，未查证的布局一律拒绝，不用"类型相同/长度相同/坐标看着合理"来猜偏移。

适用场景：HMI 文件结构取证、批量改同类控件的文字/绑定、在无 GUI 自动化（UIPI 限制）时完成文件侧工作，再向用户索取宿主观测。

## 30 秒判断是否适用

| 你的需求 | 结论 |
| --- | --- |
| 改已有标签文字、输入框绑定与上下限、标准按钮事件脚本 | ✅ 有宿主验收证据，可直接用 |
| 克隆同窗口控件、复制模板窗口建新画面 | ⚠️ 有入口，跨窗口引用/全局 ID 仍需宿主检查 |
| 改下拉框、按钮、DLL 控件的矩形 | ⚠️ 有已查证偏移的类型才放行，偏移必须由你自己取证 |
| 图形控件（直线/矩形/椭圆/位图等）任意缩放 | ❌ 仅 5004/5006 两份样本支持受限横移，其余拒绝 |
| 新建变量、改名传播、注册设备通道/新地址 | ❌ 无 CLI 入口；字节新增通道已被证明会被宿主静默丢弃 |
| 解析旧版本工程、`MCGS-ESET` 文档头、65535+ 长度扩展记录 | ❌ 明确拒绝，不做猜测降级 |
| 需要官方 API / 稳定二进制格式承诺 | ❌ 非官方逆向成果，按版本哈希锁定 |
| 当作通用 `.MCP` 编辑器批量生成整页工程 | ❌ 不是工程编译器，仍需模板 + 变量映射 + 宿主验收 |

## 能力矩阵

运行时以 `scripts/kind_registry.py` 的门禁和具体命令校验为准；本表是入口索引，不替代具体模板的取证。

| 能力 | 入口 | 证据等级 |
| --- | --- | --- |
| 数据库与完整窗口记录检查、统计分母 | `mcp_tool.py inspect` | 文件侧 + 合成测试 |
| 窗口身份/导航一致性只读检查 | `inspect --reference-profile` | 文件侧 |
| 标签改字（变长中文） | `patch` / `string`（0x5008） | 宿主验收 |
| 输入框改绑 + 上下限 | `input_binding` / `input_range`（0x5025） | 宿主验收 |
| 标准按钮事件（源码 + 编译数组） | `event`（0x5027） | 宿主验收（含 Ctrl+E） |
| 矩形编辑 | `rectangle`（5008/5025/5027/5028/503C/503D） | 宿主验收或文件侧（见 [能力清单](mcgs-mcp-editor/references/capabilities.md)） |
| 两份图形样本受限横移 | `horizontal_move`（5004/5006，92 B 指纹） | 宿主验收 + 样本锁定 |
| 其他已登记类型等长改字 | `string` | 文件侧；不证明绑定/多语言引用 |
| 同窗口控件克隆 / 模板窗口复制 | `action=clone` / `new_windows` | 宿主验收（限样本） |
| 条件脚本编译 / 静态检查 / 仿真 | `script_tool.py compile/inspect/simulate` | 原厂机器码仿真 + 合成测试 |
| 新变量、设备通道、跨窗口引用 | — | ❌ 无入口（见 [通道边界](mcgs-mcp-editor/references/device-channels.md)） |

登记类型共 **22 类**（类型身份 ≠ 可编辑能力）；`0x5026 CDrawFlow` 仅识别身份、拒绝所有显式编辑；`0x5030` 报表仍是候选、不登记；`0x5039` 只有等长文字入口。

## 快速开始

前置：Windows（`patch` 需要 Access ODBC 驱动）、Python 与驱动位数一致、自备已安装的 McgsPro 3.5.1.7267。

```powershell
git clone https://github.com/Babel36acl/mcgs-mcp-editor-skill.git
cd mcgs-mcp-editor-skill
python -m pip install -r mcgs-mcp-editor/requirements.txt

# 1) 只读盘点：窗口 ID、记录索引、类型、payload 哈希、字符串线索
python mcgs-mcp-editor/scripts/mcp_tool.py inspect D:/Experiments/sample.MCP > D:/Experiments/inventory.json

# 2) 按 inventory 写编辑清单（示例见 examples/，偏移必须自己取证）
python mcgs-mcp-editor/scripts/mcp_tool.py patch D:/Experiments/sample.MCP `
  --profile D:/Experiments/edits.json --output D:/Experiments/edited.MCP

# 3) 条件脚本：编译 → 静态检查 → 仿真（compile/simulate 需要原厂二进制）
python mcgs-mcp-editor/scripts/script_tool.py compile --source examples/script/source.txt `
  --symbols examples/script/symbols.json `
  --editor "C:/McgsPro/Program/McgsSetPro.exe" --runtime "C:/McgsPro/Program/script.dll" `
  --output D:/Experiments/program.json
python mcgs-mcp-editor/scripts/script_tool.py inspect --program D:/Experiments/program.json
```

三条硬规则：

- 工具**从不原地覆盖**输入：输出路径已存在会直接拒绝，失败产物只能用于取证。
- 编辑清单里的 `sha256` 不匹配（源文件被改过）、预期旧值不匹配、偏移越界、嵌套长度交叉，都会中止而不是"尽量写"。
- `DATABASE_ROUNDTRIP_ONLY_HOST_ACCEPTANCE_REQUIRED` 是工具返回的固定状态字：**文件回读通过 ≠ 宿主可用**。

## 安装为 Agent 技能

`mcgs-mcp-editor/` 是技能本体（`SKILL.md` + `references/` + `scripts/`）。按你的 Agent 选择安装位置：

| Agent / 运行时 | 安装目录 |
| --- | --- |
| OpenAI Codex | `~/.codex/skills/mcgs-mcp-editor/` |
| Claude Code | `~/.claude/skills/mcgs-mcp-editor/` |
| 共享 skills 目录（DSH 等） | `~/.agents/skills/mcgs-mcp-editor/` |
| 不使用技能机制 | 直接把 `scripts/` 当普通 Python 工具调用 |

```powershell
Copy-Item -Recurse mcgs-mcp-editor "$HOME/.agents/skills/"
```

技能会匹配 MCGS 文件编辑类任务。**仓库是唯一开发源**：先在仓库改 + 跑测试，再同步到安装目录，避免多处独立演进。

## 仓库结构

```text
.
├── README.md                     本文件
├── CHANGELOG.md                  受证据约束的变更记录
├── CONTRIBUTING.md               贡献与去敏规则
├── LICENSE                       GPL-3.0-or-later（仅覆盖原创内容）
├── mcgs-mcp-editor/              技能本体，整层复制即可安装
│   ├── SKILL.md                  技能入口：任务→资料路由、红线
│   ├── agents/openai.yaml        Codex 显示名与默认提示
│   ├── requirements.txt          运行时依赖
│   └── references/
│       ├── capabilities.md       入口清单与"已验/未验"分级
│       ├── format.md             Access + CArchive 记录格式、22 类注册表
│       ├── usage.md              命令、编辑清单字段、退出码
│       ├── acceptance.md         V1 损坏根因、逐阶段宿主验收记录
│       ├── validation.md         证据分层、普查分母、与第三方实现对拍
│       ├── variable-ids.md       变量 ObjData 布局与 ID/绑定线索
│       └── device-channels.md    设备通道加载丢弃、占址与验证路径
├── mcgs-mcp-editor/scripts/      纯 Python 工具（无厂商代码）
├── tests/                        合成结构/字段测试 + 可选原厂机器码测试
├── examples/                     编辑清单、引用清单、脚本样例
└── .github/workflows/ci.yml      Windows 上的多版本测试
```

## 命令行参考

### `mcp_tool.py`

| 子命令 | 关键参数 | 依赖 | 行为与退出码 |
| --- | --- | --- | --- |
| `inspect` | `mcp` | `access-parser` | 输出 JSON：`windows`（逐窗 `parsed/rejected`）、`summary`（窗口/记录/类型分母）、`complete`、`references`。默认恒返回 0 |
| | `--require-complete` | | 报告后若存在拒绝窗口，退出码 **2** |
| | `--reference-profile refs.json` / `--fail-on-reference-mismatch` | | 检查已查证的导航字段；出现 mismatch 时退出码 **3**（与 2 同时触发时 2 优先） |
| `patch` | `mcp --profile edits.json --output new.MCP [--driver ...]` | `access-parser` + Windows + `pyodbc` + Access ODBC | 只在声明字段变化且回读一致时写成功；输出已存在、路径含 `;` 或换行、源哈希变化均拒绝 |

### `script_tool.py`

| 子命令 | 需要 | 行为 |
| --- | --- | --- |
| `compile` | 厂商 `McgsSetPro.exe` + `script.dll`（SHA-256 锁定） | 在 Unicorn 内执行原厂代码生成器，输出 `program.json`（源码 + 符号 + 字节码 + 哈希） |
| `inspect` | **仅标准库** | 解码 21 种指令、校验记录帧/跳转边界/控制流栈类型，列出对象读写引用；拒绝未知指令与非零头部 |
| `simulate` | 厂商 `script.dll` | 用原解释器在内存字典上执行，不连接 HMI/设备 |

### 受限 BASIC 子集

支持：数值变量、int32 常量、加法、多语句、嵌套 `If/Else/EndIf`（≤8 层）、六种比较（`= <> < > <= >=`），源码 ≤128 非空行，字节码 13–4096 B。
不支持：函数、循环、字符串、浮点字面量、数组/局部变量、完整 BASIC。拒绝而不是降级。

## 编辑清单格式

`edits.json` 顶层：`source_sha256`、`window_id`、`controls`，可选 `new_windows`。
每个控件动作：`action`（`replace`/`clone`）、`record_index`、`kind`、`sha256`、`edits`、`nested_counts`，克隆另需 `name_offset`。

| edit type | 适用范围 | 必填 |
| --- | --- | --- |
| `string` | 全部已登记类型；变长仅 5008/5025/5027 | `offset`, `expected`, `value` |
| `rectangle` | 六类已查证 int32 矩形 | `offset`, `expected`, `value` |
| `horizontal_move` | 仅 5004/5006 的 92 B 指纹样本，且单次只能一个编辑 | `offset=12`, `expected`, `dx` |
| `input_binding` | 仅 0x5025 | 另加 `id_offset`, `expected_id`, `value_id` |
| `input_range` | 仅 0x5025，顺序 `[最大值, 最小值]` | `expected`, `value` |
| `event` | 仅 0x5027，源码与字节码一起替换 | 另加 `expected_code_sha256`, `program_file` |

完整字段说明与偏移规则见 [命令与编辑清单](mcgs-mcp-editor/references/usage.md)，可复制骨架见 [examples/](examples/README.md)。**示例中的偏移与哈希必须替换为你自己工程的取证结果。**

## 证据分级：什么叫"验证过"

本仓库把证据分成五层，任何结论都注明属于哪一层、覆盖到哪、跳过了多少：

| 层 | 手段 | 不能替代 |
| --- | --- | --- |
| 数据库 | 回读全部非系统表，比对行/列/BLOB 差异 | 控件内部结构与宿主加载 |
| 完整窗口记录 | 严格帧解析、trailer 保留、其余记录逐字节不变 | 嵌套字段语义与运行时行为 |
| 字段/引用 | 精确哈希 + 原像 + 嵌套长度 + 绑定 ID/名称 | 宿主编译与保存持久化 |
| 测试/原厂仿真 | 合成结构测试、原厂机器码执行 | 真实 GUI、设备与现场 |
| 宿主 | 打开、属性、Ctrl+E、离线输入/动作、保存关闭重开 | 真机联动验收 |

历史宿主观测是**用户对列明步骤的确认**，不是本工具生成的 GUI 轨迹；换过文件后再引用旧验收，必须重新关联产物哈希。详见 [验收记录](mcgs-mcp-editor/references/acceptance.md) 与 [多方向验证](mcgs-mcp-editor/references/validation.md)。

## 兼容性与版本锁定

- **已验证宿主**：McgsPro **3.5.1.7267**。其他版本会出现不同的记录布局，当前不承诺。
- **原厂二进制**：按 SHA-256 锁定 `McgsSetPro.exe` / `script.dll`；哈希不匹配直接拒绝，不能改哈希绕过（见 [format.md](mcgs-mcp-editor/references/format.md#原厂机器码仿真)）。
- **解析范围**：顶层窗口记录可定界读取；嵌套 payload、资源引用、变量表与设备通道只覆盖已查证字段。扩展长度（payload ≥ 65535）与 `MCGS-ESET` 文档头明确拒绝。
- **统计口径**：安装目录 18 份样例共 143 个窗口，当前解析器完整读取 136 个、拒绝 7 个，成功窗口合计 4099 条记录 / 21 类；拒绝窗口仍是未知证据，不能算作"零控件"。计数方法与陷阱见 [validation.md](mcgs-mcp-editor/references/validation.md#已知统计陷阱)。

## 安全边界与发布范围

- 只处理**用户授权的工程副本**；工具写入新路径，绝不原地覆盖。
- 不修改系统权限、不改 UAC/UIPI 设置来绕过宿主隔离；宿主 UI 受限时完成文件侧工作并列明未验项。
- 不提供厂商软件下载，不改变产品授权/许可机制，不声称官方接口。
- 发布内容只含原创工具、格式事实与**合成**测试数据；真实 MCP、厂商二进制、控件库、图片、反编译清单、包含私有变量/路径的报告一律留在本地（细则见 [CONTRIBUTING](CONTRIBUTING.md)）。
- 仿真只在 Unicorn 内执行原厂机器码，外部调用白名单仅限受限内存复制；这不构成 DLL 整体安全结论，也不代表真实设备行为。

## 开发与测试

```powershell
# 合成测试（不需要 MCGS）
python -m unittest discover -s tests -v

# 可选：原厂机器码测试（版本锁定，不匹配则失败）
$env:MCGS_EDITOR  = 'C:/McgsPro/Program/McgsSetPro.exe'
$env:MCGS_RUNTIME = 'C:/McgsPro/Program/script.dll'
python -m unittest discover -s tests -p test_native_codegen.py -v
```

当前公开打包：**37 项测试**，其中 32 项无需厂商文件即通过，5 项按环境跳过（4 项原厂机器码测试 + 1 项需要真实窗口模板的用例）。CI 在 Windows 上跑 3.10/3.12/3.14 三个版本。

## 常见问题

**`inspect` 输出里有 `status: rejected` 的窗口，能用吗？**
不能当作那部分已支持。拒绝窗口的原因是文档头、记录帧或 trailer 不符合已查证结构；默认仍返回 0 便于看部分结果，需要门禁时加 `--require-complete`（退出码 2）。

**`patch` 报 `Output exists; refusing overwrite`？**
设计如此。换新输出路径重跑；失败产物只用于取证，不要当可用工程。

**报 `Access DBQ paths containing semicolons/newlines are unsupported`？**
当前 OE 驱动的无花括号 `DBQ=` 形式无法表达分号路径。把工程放到不含 `;` 的目录。

**`pyodbc.Error` / 找不到驱动？**
需要与 Python 位数一致的 Microsoft Access ODBC 驱动（32 位 Python 配 32 位驱动），驱动名默认 `Microsoft Access Driver (*.mdb, *.accdb)`，可用 `--driver` 覆盖。

**改了控件但宿主说"工程已损坏"？**
先查是否漏更新变长字段的嵌套长度 —— V1 的真实根因就是漏了三层 `u16`，复盘见 [acceptance.md](mcgs-mcp-editor/references/acceptance.md#v1-根因)。

**为什么不能直接给我加个变量 / 加条设备通道？**
变量分配与通道注册都还没建立通用规则；字节新增通道已被实测证明会在宿主加载时被静默丢弃并在保存后删除。需要新地址时走宿主原生"增加设备通道"，见 [通道边界](mcgs-mcp-editor/references/device-channels.md)。

**`script_tool.py inspect` 需要装厂商软件吗？**
不需要。它只解析 `program.json` 里的 `code_hex`，仅用标准库；`compile`/`simulate` 才需要原厂二进制。

## 许可与商标

本仓库原创内容采用 **GNU GPL v3 或更高版本（GPL-3.0-or-later）**，全文见 [LICENSE](LICENSE)。
MCGS、昆仑通态及相关产品名称为其权利人商标；厂商 EXE/DLL、安装包、控件库、示例工程不适用本仓库 GPL，也不随仓库分发。

## 文档索引

| 想知道什么 | 读这个 |
| --- | --- |
| 现在能改什么、证据到哪一层 | [capabilities.md](mcgs-mcp-editor/references/capabilities.md) |
| 文件格式、22 类注册表、字段偏移 | [format.md](mcgs-mcp-editor/references/format.md) |
| 命令怎么用、清单怎么写、退出码 | [usage.md](mcgs-mcp-editor/references/usage.md) |
| 历史上哪次改坏了、怎么修、宿主验收记录 | [acceptance.md](mcgs-mcp-editor/references/acceptance.md) |
| 怎么做证据分层、普查分母、与第三方实现对拍 | [validation.md](mcgs-mcp-editor/references/validation.md) |
| 变量 ObjData 布局、ID 与绑定线索 | [variable-ids.md](mcgs-mcp-editor/references/variable-ids.md) |
| 设备通道为什么会被丢弃、新地址怎么办 | [device-channels.md](mcgs-mcp-editor/references/device-channels.md) |
| 给 Agent 的执行红线 | [SKILL.md](mcgs-mcp-editor/SKILL.md) |
