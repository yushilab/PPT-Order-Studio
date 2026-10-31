# PPT Order Studio

把客户资料变成可编辑 PPT 的本地工作流：**资料整理 → 内容规划 → 3～5 页样张 → 客户确认 → 全稿 → 修改交付**。

这是一个 Python 工具项目，同时提供 AI 可读的操作指南和工作流 Skill。AI 负责理解、写作与设计；本地命令负责资料缓存、状态管理、页面生成、基础检查和交付。项目本身不调用模型 API，不需要 API Key。

**设计方式可选：默认使用内置生成器，也可按订单启用 PPTAgent Skill。** 第一轮样张不满意时，可以开始新一轮、换一种方式，保留旧方案并重新确认设计。PPTAgent 的安装、开关和操作见 [设计引擎指南](docs/design-engines.md)。

## 先选你的使用方式

| 当前 AI 环境的能力 | 怎么使用 |
|---|---|
| 能读取项目文件、写入文件、运行终端命令 | 让 AI 从 [AI_START_HERE.md](AI_START_HERE.md) 开始，完成检查和订单操作。 |
| 能读取上传文件，但不能运行本地命令 | 手动运行本项目，把生成的上下文文件上传给 AI，再将 AI 返回的 JSON 保存到订单中。见 [桌面 AI 配合方式](docs/desktop-ai.md)。 |
| 只能聊天 | 复制相关上下文和规范给 AI，按提示手动保存结果、运行命令。 |

ChatGPT、豆包、Gemini 的桌面应用和代理环境具有不同的文件及执行能力，且随版本、账号和设置变化。**安装桌面应用并不等于它能控制本机终端。** 本项目会先确认实际能力，再选择自动或手动路线。

## 快速开始

先把项目下载或克隆到本机目录，进入项目根目录。准备 **Python 3.10 或更高版本**；Git 只在克隆和开发时需要。生成 PPTX 不要求安装 PowerPoint，视觉检查和最终精修建议使用客户的目标软件。

仓库：[yushilab/PPT-Order-Studio](https://github.com/yushilab/PPT-Order-Studio)。

```bash
git clone https://github.com/yushilab/PPT-Order-Studio.git
cd PPT-Order-Studio
```

也可在 GitHub 仓库页面通过 **Code → Download ZIP** 下载并解压，随后进入项目根目录。

Windows PowerShell：

```powershell
./bootstrap.ps1
./.venv/Scripts/python.exe -m pptstudio doctor
./.venv/Scripts/python.exe -m pptstudio demo orders/demo
```

macOS / Linux：

```bash
bash bootstrap.sh
./.venv/bin/python -m pptstudio doctor
./.venv/bin/python -m pptstudio demo orders/demo
```

脚本在项目内创建 `.venv` 并安装依赖，不要求激活环境。若系统拦截 PowerShell 脚本，可按 [安装说明](docs/setup.md) 使用逐条 Python 命令，无需修改全局执行策略。

`demo` 创建虚构资料和五页演示订单，并生成草稿 PPTX；命令会报告实际输出位置。打开生成的文件，检查字体、图表、布局和可编辑性。**示例不会伪造客户确认，也不能直接作为已验收交付稿。**

仓库还附带已生成的 [五页草稿 PPTX](examples/rendered/demo-draft.pptx) 和 [PowerPoint 导出的 PDF 预览](examples/rendered/demo-preview.pdf)，可先看实际输出。它们是流程与组件示例，具体订单可调整视觉规范或扩展布局。

## 开始一单真实业务

下文的 `python` 指项目虚拟环境中的 Python；Windows 对应 `./.venv/Scripts/python.exe`，macOS/Linux 对应 `./.venv/bin/python`。

```bash
python -m pptstudio init orders/client-a --title "年度经营汇报" --pages 20 --audience "管理层"
```

将客户原始资料复制到 `orders/client-a/sources/`，完善订单内的 `brief.json`，再运行：

```bash
python -m pptstudio ingest orders/client-a
python -m pptstudio context orders/client-a --stage analyze --max-chars 24000
```

让 AI 阅读生成的上下文，填写 `facts.json`；然后生成规划上下文，让 AI 按 [数据格式](docs/data-format.md) 填写 `deck.json`：

```bash
python -m pptstudio context orders/client-a --stage plan --max-chars 24000
python -m pptstudio validate orders/client-a --outline
```

客户确认大纲后，由操作者记录真实确认：

```bash
python -m pptstudio approve orders/client-a --scope plan --by "操作者" --client-confirmed
python -m pptstudio sample orders/client-a --slides S01,S06,S12
python -m pptstudio render orders/client-a --sample
```

打开并检查样张，给客户确认。按反馈修改后重新生成，直到通过，再记录样张确认：

```bash
python -m pptstudio approve orders/client-a --scope design --by "操作者" --client-confirmed
python -m pptstudio context orders/client-a --stage build --slides S02,S03,S04,S05 --max-chars 18000
python -m pptstudio build orders/client-a
python -m pptstudio qa orders/client-a
python -m pptstudio render orders/client-a
```

先逐批填写全部页面，再生成完整文稿并检查；`build` 会验证全稿内容，不能仅凭一批页面生成已完成全稿。完成后，在目标 PowerPoint/WPS 中人工检查和精修；若修改了 PPTX，使用 `baseline` 登记该文件，见 [完整工作流](docs/workflow.md)。客户最终验收后，再记录最终确认并打包：

```bash
python -m pptstudio approve orders/client-a --scope final --by "操作者" --client-confirmed --visual-reviewed
python -m pptstudio package orders/client-a
```

`approve` 是操作者对已经发生的确认进行登记。AI 只能在用户明确说明客户已确认后记录，不能自行决定通过。`--draft` 用于试做和开发验证，不代替上述确认。

## v0.2 的范围

- 本地订单、资料解析与增量缓存、来源回查、按阶段及页面准备有限长度上下文。
- JSON 驱动的可编辑 PPTX：封面、要点、指标、图表、图片、时间轴、结束页。
- 大纲、样张和最终确认记录；内容变化后的确认有效性检查。
- 基础版面检查、可选渲染、人工精修基准、反馈及用量记录、交付打包。
- 项目内的通用操作文档和可选工作流 Skill。
- 可选 PPTAgent 设计后端、项目默认值、订单覆盖、设计轮次归档及恢复。

人工或 AI 仍负责内容分析和设计决策。PPTAgent 模式由宿主 AI 编写 HTML/CSS，完成真实渲染、审阅和转换后导入 PPTX；它不自动调用在线模型。其可选运行环境需要 Linux/WSL 或 macOS，原生 Windows 可继续使用内置生成器。普通安装不会下载其运行依赖。

本项目没有可视化订单后台、自动客户沟通或图片生成服务；扫描件会明确标记需要 OCR。任意复杂模板的无损编辑、像素级还原、自动证明文字不溢出，也不属于本版承诺。

## 文档入口

- [给 AI 的启动指令](AI_START_HERE.md)
- [简明使用指南和可复制提示词](AI_QUICKSTART.md)
- [从创建订单到交付的 AI 使用手册](AI_USER_GUIDE.md)
- [环境安装、迁移和故障排查](docs/setup.md)
- [完整流程、客户确认和修改回退](docs/workflow.md)
- [PPTAgent 开关、设计切换及历史恢复](docs/design-engines.md)
- [JSON 格式与页面示例](docs/data-format.md)
- [CLI 命令速查](docs/cli.md)
- [ChatGPT / 豆包 / Gemini 配合方式](docs/desktop-ai.md)
- [Token 和成本控制](docs/token-budget.md)
- [贡献与测试](docs/contributing.md)
- [本版实测记录](docs/validation.md)
- [开源发布与下一版计划](docs/publishing.md)

代码按 [MIT License](LICENSE) 发布。客户资料、订单和生成的交付文件属于使用者，应保存在被 Git 忽略的 `orders/` 内；发布项目代码前检查暂存文件清单。
