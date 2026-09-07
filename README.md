# MCGS MCP Editor Skill

用于 Codex 的 MCGS Pro `.MCP` 文件编辑技能与 Python 工具。这里的 MCP 是 MCGS 的 Access 工程文件，不是 Model Context Protocol。

目前针对 **McgsPro 3.5.1.7267** 验证了标签文字、数值输入框绑定及上下限、标准按钮源码与字节码替换、受限 `If/Else` 条件脚本，以及保存关闭重开。工具优先直接修改工程副本，适合 UI 自动化受 UIPI 限制的工作方式。

本仓库包含原创解析/编辑脚本、受限前端、原厂代码的 CPU 仿真调用器和合成测试。**不包含厂商 EXE/DLL、安装包、真实 MCP 工程或用户截图。** 使用者自行提供已安装的匹配版本。MIT 许可证只覆盖本仓库原创内容。

这是非官方工具；MCGS 相关产品及商标归各自权利人所有，厂商程序不适用本仓库 MIT 许可。

## 安装

将 `mcgs-mcp-editor` 目录复制到 `~/.codex/skills/`，即可作为 `$mcgs-mcp-editor` 使用。技能可以自动匹配 MCGS 文件编辑任务。

```powershell
python -m pip install -r mcgs-mcp-editor/requirements.txt
python mcgs-mcp-editor/scripts/mcp_tool.py --help
python mcgs-mcp-editor/scripts/script_tool.py --help
```

数据库写入需要 Windows、与 Python 位数匹配的 Access ODBC 驱动。阅读 [工具用法](mcgs-mcp-editor/references/usage.md) 后准备真实工程的显式编辑清单；合成示例的偏移和哈希不能直接用于真实 MCP。

## 证据与范围

- [技能入口](mcgs-mcp-editor/SKILL.md)
- [文件格式、版本哈希与未覆盖范围](mcgs-mcp-editor/references/format.md)
- [V1 损坏根因、控制实验及宿主验收](mcgs-mcp-editor/references/acceptance.md)

原厂代码生成器在 Unicorn 中生成操作码和分支位移；解释器仿真使用内存数值对象，不执行真实设备 I/O。它是受限 BASIC 子集，不是完整工程编译器或官方 API。真实页面仍需模板、变量映射和宿主验收，不能把数据库可读等同于工程有效。

## 测试

```powershell
python -m unittest discover -s tests -v
$env:MCGS_EDITOR = 'C:\McgsPro\Program\McgsSetPro.exe'
$env:MCGS_RUNTIME = 'C:\McgsPro\Program\script.dll'
python -m unittest discover -s tests -p test_native_codegen.py -v
```

未提供本地二进制时，原厂仿真测试明确跳过；其他合成测试不需要 MCGS。开启原厂测试后，SHA-256 不匹配会失败。
