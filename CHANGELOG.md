# 变更记录

本项目的版本线跟随**已查证的格式事实与门禁**，不跟随功能数量。每条变更注明证据层级；未验证的内容不进 `已支持`。

## 0.5.3 — 2026-11-13

### 仓库结构
- 技能目录迁移为 `skills/mcgs-mcp-editor/`（标准 `<容器>/<技能名>/SKILL.md` 布局）。`npx skills add` 现在直接命中标准位置，不再依赖"标准位置无结果才递归搜索"的回退。
- 同步更新 README（仓库结构树、安装命令、复制路径）、`usage.md` 示例命令、`examples/README.md`、CI 冒烟路径，以及全部测试的 `sys.path`。

## 0.5.2 — 2026-11-13

### 覆盖范围与发布
- README 新增「覆盖范围与迭代」：明确结论来自手头工程副本，不代表 MCGS Pro 全功能（报表/配方/曲线/报警、变量与通道创建等仍缺证据），欢迎按证据分层补 issue/PR。
- README 新增「进阶：继续逆向 MCGS Pro（推荐 REA）」：给出 `open_binary` → `search_procedures`/`analyze_function`/`xrefs`/`trace_feature` → `inspect_pe_resources`/`search_bytes` → Frida/GDB 单字段对照的可执行路线，并声明 REA 输出属未验证材料。
- 新增 skills.sh 安装入口（`npx skills add Babel36acl/mcgs-mcp-editor-skill --skill mcgs-mcp-editor`）；该目录无需提交，安装事件即索引来源。
- `SKILL.md` 描述补充覆盖范围声明与 REA 使用指引；`CONTRIBUTING.md` 增加"以证据为界、欢迎迭代"章节。

## 0.5.1 — 2026-11-13

### 脱敏（去除工程相关信息）
- `acceptance.md`：失败版本代号改为通用描述（内部链接同步为「一次损坏版本的根因」）；移除工程标签、示例画面名、UI 动作原文与具体窗口/记录计数，改为"窗口 +1、记录 +2"等通用描述。
- `variable-ids.md`：示例变量名改为「一个新增整数变量」；工作区文件计数改为"若干副本"。
- `capabilities.md` / `device-channels.md` / `validation.md`：移除内部实验批次标签与指向具体工程交付物的措辞，统一改为"操作者确认/宿主反馈"。
- 全仓库复核：无工程名、画面名、变量名、工程产物哈希、本机路径；保留厂商二进制版本锁哈希与厂商样例统计。

### 依赖说明
- README、`references/usage.md`、`SKILL.md`、`requirements.txt` 增加依赖与 Access ODBC 驱动说明：`inspect` 无需驱动；`patch` 需要 Windows + 与 Python 位数一致的 Access 驱动（ACE/Office 提供，非 pip 包、不可分发）；含 `pyodbc.drivers()` 自检与 `IM002`/`IM014` 等报错对照。
- `CONTRIBUTING.md` 去敏清单补充"画面名、变量名、工程结构计数"。

## 0.5.0 — 2026-11-13

### 文档与仓库
- README 重写：能力矩阵、30 秒适用性判断、快速开始、命令行/退出码参考、FAQ、文档索引；补齐"证据分级"与去敏发布范围。
- 新增 `CONTRIBUTING.md`（含提交前去敏自查）、`CHANGELOG.md`、`examples/`（编辑清单 / 引用清单 / 脚本样例）。
- 新增 GitHub Actions CI（Windows，Python 3.10/3.12/3.14），只跑离线合成测试；原厂机器码测试按环境变量跳过。
- `references/variable-ids.md` 去敏：移除工程代号、样本名与私有产物哈希，改为通用描述。
- `references/capabilities.md`、`validation.md`、`variable-ids.md` 首次随仓库发布。

### 工具
- `mcp_tool.py inspect`：逐窗 `parsed/rejected` 状态、`summary` 分母统计、`complete` 标志；新增 `--require-complete`（退出码 2）与 `--reference-profile` / `--fail-on-reference-mismatch`（退出码 3）。
- 新增 `reference_check.py`：只读检查窗口行/trailer 身份、名称与 ID 唯一性，以及按精确哈希清单定位的窗口导航字段；未知布局记为未覆盖，不自动修补。
- 新增 `shape_geometry.py` + `horizontal_move`：仅 5004/5006 的 92 B 指纹样本，横向原点归一化后比对完整 payload，锁定尺寸/纵坐标/样式/名称。
- `kind_registry`：登记第 22 类 `0x5026 CDrawFlow`（身份成立、无已验证可写布局，全部显式编辑拒绝）；`rectangle` 门禁维持六类。
- 测试：22 类注册表断言、0x5026 全拒绝、`horizontal_move` 门禁与负例、引用检查（一致/不一致/未覆盖/清单过期）合成用例。

## 0.4.0 — 2026-10-17
- 审查字段布局与原生装配证据，同步技能边界；`format.md` 补充 0x5026 身份/布局分离结论与 5039 动作差分样本。
- 通道创建结论由"文件侧成功"修正为"宿主静默丢弃"，明确新地址走宿主原生流程。

## 0.3.0 — 2026-10-16
- `kind_registry`：新增 11 类中的 10 类补齐等长多记录字段分组线索。
- 文档：修正通道创建结论，补充宿主验证边界。

## 0.2.0 — 2026-10-16
- 21 种窗口类型注册表与分级放行；模板窗口复制（`new_windows`）经宿主打开、Ctrl+E、保存重开验收。
- `bytecode_inspect.py`：21 种指令解码、跳转边界与栈类型检查，无需原厂依赖。

## 0.1.0 — 2026-09-07
- 首个公开版本：MCP 窗口记录解析、控件字段校验与补丁、受限 BASIC 条件脚本生成/仿真。
- 许可证切换为 GPL-3.0-or-later。