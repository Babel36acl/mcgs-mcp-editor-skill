# 命令与编辑清单

以下命令从仓库根目录执行。输出文件须为新路径。工具不会原地覆盖输入 MCP。

## 读取工程

```powershell
python mcgs-mcp-editor/scripts/mcp_tool.py inspect D:/Experiments/sample.MCP > D:/Experiments/inventory.json
```

清单包含窗口 ID、记录索引、类型、payload 哈希和字符串候选。候选包含脚本等工程内容，属于使用者的本地资料，不应随公共仓库提交。普通字符串扫描会跳过带控制字符的多语言引用。

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
python mcgs-mcp-editor/scripts/script_tool.py simulate --program D:/Experiments/program.json --values D:/Experiments/values.json --runtime C:/McgsPro/Program/script.dll
```

`program.json` 把源码、符号映射、字节码和生成器哈希放在同一文件。仿真数据由 JSON 提供，不连接 HMI 或控制器。支持的条件为数值原子之间的 `= <> < > <= >=`，赋值右侧支持原子和加法。`If` 最多嵌套 8 层，源码最多 128 个非空行；拒绝未支持语法，不默默降级。

## 编辑 MCP 副本

编辑清单中的偏移均相对于**修改前的完整控件 payload**。同一控件的多个编辑统一按原偏移执行，不需要手工补偿前面字符串带来的偏移变化。

顶层对象包含 `source_sha256`、`window_id` 和 `controls`。每个控件动作包含：

| 属性 | 含义 |
| --- | --- |
| action | `replace` 或同窗口 `clone` |
| record_index / kind | 原记录索引及类型，例如 `"0x5008"` |
| sha256 | 原 payload 的精确 SHA-256 |
| edits | 下表中的显式字段编辑 |
| nested_counts | 覆盖变长字段的所有嵌套 u16 计数字段；每项为 `offset` 和 `expected` |
| name_offset | clone 必需：原控件名称字符串偏移；edits 必须包含唯一新名称 |

| 编辑 type | 其他字段 |
| --- | --- |
| string | `offset`, `expected` 原文字, `value` 新文字 |
| rectangle | `offset`, `expected` 原 `[l,t,r,b]`, `value` 新矩形 |
| input_binding | `offset`, `expected` 原变量名, `value` 新变量名；另给 `id_offset`, `expected_id`, `value_id` 同步绑定对象 ID |
| input_range | `offset`, `expected` 原 `[max,min]`, `value` 新范围 |
| event | `offset` 源码字符串位置, `expected` 原源码, `expected_code_sha256` 原字节数组哈希, `program_file` 相对本清单的生成报告路径 |

JSON 可以组合标签改字、输入框 input_binding 改绑与 input_range、按钮 event。绑定时同步名称和对象 ID，不依赖宿主替你修补旧 ID。`nested_counts` 不是自动推断结果，必须来自模板取证，尤其不能省略按钮样式内部的长度字段。只编辑不在数组内的字段时可为空。

```powershell
python mcgs-mcp-editor/scripts/mcp_tool.py patch D:/Experiments/sample.MCP --profile D:/Experiments/edits.json --output D:/Experiments/edited.MCP
```

Python API 同样可用：`mcp_tool.inspect(path)`、`mcp_tool.patch(source, output, profile, driver)`、`control_patch.patch_payload(payload, profile)`。API 的 event 使用 `program` 字典；CLI 从 `program_file` 读取该字典。工具返回数据库回读状态，不声称宿主已验收。

修改失败时保留输出用于取证，不能把残留文件视作可用结果。换一个新输出路径重新生成。克隆会完整继承原资源、绑定和脚本；先检查继承语义及未解释引用，再做宿主验收。

## 发布范围

公开贡献只应包含原创工具、格式事实和合成样本。真实 MCP、厂商二进制、控件库、资源图片、反汇编清单以及包含私有变量/路径的分析报告留在使用者的本地目录。本工具不提供厂商软件下载，不改变产品授权机制，也不代表厂商官方接口或兼容承诺。
