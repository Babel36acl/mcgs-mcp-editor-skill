# 示例

这些文件是**骨架**：偏移、哈希、符号 ID 全部是占位值，直接运行必然被工具拒绝——这是设计目标，不是缺陷。

| 文件 | 用途 | 怎么变成可用的 |
| --- | --- | --- |
| `edit-profile.example.json` | 一个控件替换 + 一个模板窗口复制的清单骨架 | 用 `mcp_tool.py inspect` 拿到你的 `source_sha256` / `record_index` / `sha256` / 字符串偏移，替换全部 `REPLACE_ME` 与本示例偏移 |
| `reference-profile.example.json` | 只读导航字段检查清单（`--reference-profile`） | 先用精确偏移与哈希定位来源控件里的目标窗口名与 ID，再替换 |
| `script/source.txt` + `symbols.json` + `values.json` | 条件脚本编译/仿真的最小输入 | 把 `symbols.json` 换成你工程里真实变量名 → 脚本对象 ID 的映射（必须逐工程查证） |

## 一个最小可行流程

```powershell
# 1) 盘点（只读）
python mcgs-mcp-editor/scripts/mcp_tool.py inspect D:/Experiments/sample.MCP > D:/Experiments/inventory.json

# 2) 从 inventory.json 抄出：文件 sha256、目标窗口 id、目标控件 record_index/kind/sha256
#    再用 read_string 定位字段偏移（不是猜）
python -c "import json;s=json.load(open('D:/Experiments/inventory.json',encoding='utf-8'));print(s['sha256']);print(json.dumps(s['windows'][0]['records'][0],ensure_ascii=False,indent=1))"

# 3) 改写 examples/edit-profile.example.json 里的占位值 → 你的 edits.json

# 4) 写入新文件（Windows + Access ODBC 驱动）
python mcgs-mcp-editor/scripts/mcp_tool.py patch D:/Experiments/sample.MCP `
  --profile D:/Experiments/edits.json --output D:/Experiments/edited.MCP

# 5) 宿主验收：打开 → 属性 → Ctrl+E → 动作/输入 → 保存关闭重开 → 再回读比对
```

## 别把这些示例当格式文档

- `nested_counts` 必须来自**你那份模板**的取证，省略或乱填会导致"工程已损坏"。
- `input_range` 的存储顺序是 `[最大值, 最小值]`，不是 `[最小值, 最大值]`。
- `event` 的 `program_file` 由 `script_tool.py compile` 生成，`expected_code_sha256` 是**旧的编译数组**哈希。
- 校验失败时保留输出用于取证，换新路径重跑；不要在同一条路径上反复覆盖。
