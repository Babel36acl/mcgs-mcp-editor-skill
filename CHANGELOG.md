# 变更记录

本项目的版本线跟随**已查证的格式事实与门禁**，不跟随功能数量。每条变更注明证据层级；未验证的内容不进 `已支持`。

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