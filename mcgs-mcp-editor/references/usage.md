# 命令与编辑清单

以下命令从仓库根目录执行；安装后使用技能目录下相同的 `scripts/` 入口。输出文件须为新路径。工具不会原地覆盖输入 MCP。

## 读取工程

```powershell
python mcgs-mcp-editor/scripts/mcp_tool.py inspect D:/Experiments/sample.MCP > D:/Experiments/inventory.json
```

清单包含窗口 ID、记录索引、类型、payload 哈希和字符串候选。每个窗口有 `status=parsed/rejected`，顶层 `summary` 给出窗口总数、成功数、拒绝数、成功窗口内的记录数及类型计数，`complete` 仅表示本解析器是否完整读取所有窗口。失败记录保留异常类型和原因；不能把拒绝窗口算作零控件。候选包含脚本等工程内容，属于使用者的本地资料，不应随公共仓库提交。普通字符串扫描会跳过带控制字符的多语言引用。

自动流程需要完整窗口解析时加 `--require-complete`：输出报告后，只要存在拒绝窗口就以退出码 2 结束。默认 inspect 保留原退出行为，便于读取部分成功结果；两种模式都不修改 MCP。

```powershell
python mcgs-mcp-editor/scripts/mcp_tool.py inspect D:/Experiments/sample.MCP --require-complete > D:/Experiments/inventory.json
```

`complete=true` 不等于全部内部字段、变量引用或宿主行为通过；它只覆盖当前顶层窗口记录格式。

### 窗口身份与明确导航字段

`references` 独立输出 `consistent`、`mismatch`、`not_covered`。默认比较已识别 trailer 中的窗口名称/ID 与窗口行，同时检查重复窗口名称/ID。定位 trailer 以前必须完整解析窗口记录；拒绝窗口和未知尾部布局都保留为未覆盖。

已从取证确定导航字段位置时，可传 `--reference-profile refs.json`。清单顶层为精确 `source_sha256` 和非空 `links` 数组；每项包含：

| 属性 | 含义 |
| --- | --- |
| type | 固定为 `window_navigation` |
| window_id / record_index / kind | 来源窗口、完整记录索引、类型 |
| sha256 | 来源控件完整 payload 的 SHA-256 |
| name_offset / id_offset | 已确定的目标窗口名称 CArchive 字符串与 u32 ID 在 payload 中的位置 |

工具从实际字节读取名称/ID，并检查它们是否指向唯一的同一窗口；缺失、重复或名字与 ID 指向不同窗口均报告 mismatch。清单过期、字段越界或来源窗口无法完整解析时拒绝检查。清单是字段位置证据，不是自动导航识别器；不能把任意同名文本当导航。

```powershell
python mcgs-mcp-editor/scripts/mcp_tool.py inspect D:/Experiments/sample.MCP --reference-profile D:/Experiments/refs.json --fail-on-reference-mismatch
```

`--fail-on-reference-mismatch` 在报告后以退出码 3 表示发现不一致；同时启用 `--require-complete` 且有记录解析拒绝时优先返回 2。没有 mismatch 仍可能存在 not_covered；变量绑定、资源引用、未提供清单的导航、删除行语义和宿主行为均不在当前引用检查范围。默认 inspect 不因引用不一致改变退出码。

模板窗口复制原样保留旧 trailer，可能被新身份检查报告名称/ID 不一致；此发现不触发自动写回，也不能单凭它推定宿主必然损坏。仍须按当前产物检查宿主保存后的变化。

## 生成及模拟脚本

准备 UTF-8 源码和数字符号映射，例如：

```basic
If Result = 100 Then
  Result = 200
Else
  Result = 100
EndIf
```

`symbols.json` 使用 `{"Result": 7}`；这里的 7 仅是合成示例，真实工程必须重新查证。`values.json` 使用 `{"7": 0}`。

```powershell
python mcgs-mcp-editor/scripts/script_tool.py compile --source D:/Experiments/script.txt --symbols D:/Experiments/symbols.json --editor C:/McgsPro/Program/McgsSetPro.exe --runtime C:/McgsPro/Program/script.dll --output D:/Experiments/program.json
python mcgs-mcp-editor/scripts/script_tool.py inspect --program D:/Experiments/program.json
python mcgs-mcp-editor/scripts/script_tool.py simulate --program D:/Experiments/program.json --values D:/Experiments/values.json --runtime C:/McgsPro/Program/script.dll
```

`program.json` 把源码、符号映射、字节码和生成器哈希放在同一文件。仿真数据由 JSON 提供，不连接 HMI 或控制器。支持的条件为数值原子之间的 `= <> < > <= >=`，赋值右侧支持原子和加法。`If` 最多嵌套 8 层，源码最多 128 个非空行；拒绝未支持语法，不默默降级。

`inspect` 只需要 Python 标准库，接受带 `code_hex` 的生成报告。它解码当前数值子集的 21 种指令，返回偏移、操作数、原解释器处理地址、相对跳转目标、数值对象读写引用及控制流栈类型；拒绝截断指令、未知操作码、跳入操作数或程序头、类型不符及控制流合流时不一致的栈。偏移从整个字节码文件开头计算，包含 12 字节程序头；跳转基准是操作数结束位置。

此检查仅接受当前生成器使用的零返回类型、零参数、零局部变量头部。结果中的对象 ID 是静态引用，条件分支可能不执行相应读写；检查不证明循环终止、源码与字节码相等、对象在 MCP 中存在或 McgsPro 已验收。`max_stack_slots` 和栈检查只针对可达路径，`unreachable_offsets` 单独列出其余已解码指令。程序接口仍保留原有机器码仿真时限，源码行数上限不保证每个复杂脚本都能在该时限内生成。

Python 调用入口为 `bytecode_inspect.inspect_program(code: bytes)`，返回可序列化为 JSON 的字典。该读取器不加载厂商 DLL，也不访问实时数据库。

## 编辑 MCP 副本

编辑清单中的偏移均相对于**修改前的完整控件 payload**。同一控件的多个编辑统一按原偏移执行，不需要手工补偿前面字符串带来的偏移变化。

顶层对象包含 `source_sha256`、`window_id` 和 `controls`。每个控件动作包含：

| 属性 | 含义 |
| --- | --- |
| action | `replace` 或同窗口 `clone` |
| record_index / kind | 原记录索引及类型，例如 `"0x5008"`；类型须已登记（当前 22 类），且操作通过该类门禁；0x5026 当前仍拒绝所有显式字段编辑 |
| sha256 | 原 payload 的精确 SHA-256 |
| edits | 下表中的显式字段编辑 |
| nested_counts | 覆盖变长字段的所有嵌套 u16 计数字段；每项为 `offset` 和 `expected` |
| name_offset | clone 必需：原控件名称字符串偏移；edits 必须包含唯一新名称 |

| 编辑 type | 其他字段 |
| --- | --- |
| string | `offset`, `expected` 原文字, `value` 新文字 |
| rectangle | `offset`, `expected` 原 `[l,t,r,b]`, `value` 新矩形 |
| horizontal_move | 仅样本限定的 5004/5006：`offset=12`, `expected` 原 `[l,t,r,b]`, `dx` 有符号整数；不接受 value/dy 等其他字段 |
| input_binding | `offset`, `expected` 原变量名, `value` 新变量名；另给 `id_offset`, `expected_id`, `value_id` 同步绑定对象 ID |
| input_range | `offset`, `expected` 原 `[max,min]`, `value` 新范围 |
| event | `offset` 源码字符串位置, `expected` 原源码, `expected_code_sha256` 原字节数组哈希, `program_file` 相对本清单的生成报告路径 |

JSON 可以组合标签改字、输入框 input_binding 改绑与 input_range、按钮 event。除当前拒绝显式编辑的 0x5026 外，新类型（标签/输入框/按钮之外）的文字编辑只允许等长；`rectangle` 只允许已查证四个 int32 矩形的类型，偏移仍由样本查证：标签已验收样本为 +12，下拉框样本为 +24，DLL 控件存在 +12 和 +24 两种布局，不统一套 +24。正式 rectangle 六类及各布局的实验/宿主证据见 [能力清单](capabilities.md)。5004/5006 另有样本指纹限定的 horizontal_move；其余图形几何候选没有因此获得正式 CLI 入口。horizontal_move 的控件清单必须含 kind，单控件只允许一个横移编辑且不带 nested_counts；尺寸、纵坐标、样式及名称均锁定，不能借此缩放或改名。候选 `0x5030` 继续拒绝。`input_binding`/`input_range` 仅 0x5025，`event` 仅 0x5027。顶层可选 `new_windows` 数组建窗口，每项为 `template_window_id`、`new_name`、可选 `note`；新窗口复制模板窗口内容原样，窗口名必须唯一，内部控件名重复由宿主验收覆盖。绑定时同步名称和对象 ID，不依赖宿主替你修补旧 ID。`nested_counts` 不是自动推断结果，必须来自模板取证，尤其不能省略按钮样式内部的长度字段。只编辑不在数组内的字段时可为空。

```powershell
python mcgs-mcp-editor/scripts/mcp_tool.py patch D:/Experiments/sample.MCP --profile D:/Experiments/edits.json --output D:/Experiments/edited.MCP
```

Python API 同样可用：`mcp_tool.inspect(path)`、`mcp_tool.patch(source, output, profile, driver)`、`control_patch.patch_payload(payload, profile)`。API 的 event 使用 `program` 字典；CLI 从 `program_file` 读取该字典。工具返回数据库回读状态，不声称宿主已验收。

修改失败时保留输出用于取证，不能把残留文件视作可用结果。换一个新输出路径重新生成。克隆会完整继承原资源、绑定和脚本；先检查继承语义及未解释引用，再做宿主验收。

## 变量和设备通道请求

`input_binding` 只修改画面控件的既有变量引用；`new_windows` 只复制窗口。两者都不会创建 `System` 表中 `strName=ObjData` 记录内的变量或注册设备通道。CLI 当前没有新变量或设备通道创建入口，不要在清单中加入自造的通道字段并认为工具会处理。

涉及新地址、通道别名、设备绑定或从模板搭建工程时，先读 [通道加载与验证边界](device-channels.md)。字节新增通道曾在数据库回读正常后被宿主静默丢弃并在保存时删除；新增地址使用宿主原生流程。现有地址库内改别名、换绑定仍属待验实验，不能因为早期克隆报告成功就免除保存重开及 CSV 复验。

## 发布范围

公开贡献只应包含原创工具、格式事实和合成样本。真实 MCP、厂商二进制、控件库、资源图片、反汇编清单以及包含私有变量/路径的分析报告留在使用者的本地目录。本工具不提供厂商软件下载，不改变产品授权机制，也不代表厂商官方接口或兼容承诺。
