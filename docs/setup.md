# 安装与换电脑

## 必需和可选环境

| 环境 | 用途 | 是否必需 |
|---|---|---|
| Python 3.10+、pip、venv | CLI、文件整理、生成 PPTX | 必需 |
| `python-pptx`、`Pillow` | 原生文字、形状、图表、图片和 PPTX 文件 | 核心依赖 |
| `python-docx`、`openpyxl`、`pypdf` | DOCX、XLSX、PDF 提取 | 使用对应材料时安装 `extract` 扩展 |
| PowerPoint 或 LibreOffice | 可选的自动渲染/导出；平台支持以 `doctor` 和实际执行为准 | 可选 |
| PowerPoint/WPS 等客户目标软件 | 人工视觉检查、兼容性验证和精修 | 交付前建议具备 |
| Git | 拉取更新、版本管理、贡献代码 | 可选 |

本项目核心不需要 Node.js、模型 API Key 或其他平台的订阅。使用某个 AI 产品的费用和权限由该产品决定。

## Windows

在系统安装 Python 后，进入项目根目录运行：

```powershell
./bootstrap.ps1
./.venv/Scripts/python.exe -m pptstudio doctor
```

若 PowerShell 不允许运行脚本，直接逐条执行：

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install --upgrade pip
./.venv/Scripts/python.exe -m pip install -e ".[extract]"
./.venv/Scripts/python.exe -m pptstudio doctor
```

某些系统使用 `py -3` 而非 `python` 创建环境。安装依赖和后续命令仍使用 `.venv/Scripts/python.exe`，避免装进另一个 Python。

## macOS / Linux

```bash
bash bootstrap.sh
./.venv/bin/python -m pptstudio doctor
```

手动等价步骤：

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[extract]"
```

Linux 若缺少 `venv`，按当前发行版官方说明安装对应 Python venv 包。自动脚本不会提升管理员权限安装系统软件。

## 可选：安装项目内 Skill

```bash
python scripts/install_skill.py
```

从虚拟环境运行该命令，按输出检查目标。默认安装项目的 workflow 和 design 两个路由 Skill 到本仓库的 `.agents/skills/`，不会修改用户全局配置。可用 `--skill workflow` 或 `--skill design` 只安装一个；更新已安装的项目 Skill 时用 `--force`。其他应用直接阅读 `AI_START_HERE.md` 即可。源码在 `skills/`，PPTAgent 上游只在订单启用后按需读取。

## 可选：PPTAgent 设计环境

默认 `builtin` 只需上述基础环境。选择 PPTAgent 时，需在 Linux/WSL 或 macOS 中准备 Python 3.11+、Node/npm、LibreOffice 和独立运行依赖；执行 `python scripts/setup_pptagent.py --check` 查看缺项，明确需要使用时再按 [设计引擎指南](design-engines.md) 安装。它不会通过普通 bootstrap 自动安装，也不会修改全局 Skill。

## 渲染与字体

生成 `.pptx` 本身不依赖 Office。`render` 会尝试可用后端导出 PDF；v0.1 不自动生成逐页 PNG。没有可用后端时不能据此认定 PPT 的视觉质量通过。可用 PowerPoint/WPS 手动导出 PDF 或逐页图片后核对。渲染样张时加 `--sample`，否则命令检查当前全稿或人工基准。

字体通过 `style.json` 的 `font` 指定。项目不分发商业字体，也不保证该字体在客户电脑存在。首次样张就在目标环境验证中文字体，最终兼容性检查保留在交付流程中。

## 迁移和更新

换电脑时复制项目代码和需要继续制作的订单，重新创建 `.venv`；不要复制旧电脑的虚拟环境。订单内路径尽量使用相对路径，图片保存在订单目录中。客户要求的备份或传输方式由操作者决定，项目不会自动上传。

更新前备份订单与人工精修基准。获取代码更新后，在原虚拟环境执行 `python -m pip install -e ".[extract]"`，再运行 `doctor` 和测试订单。

## 常见问题

- **缺少某个提取库**：用当前 `.venv` 安装 `.[extract]`，然后重新 `ingest`。检查每份资料状态，不把依赖缺失当成空内容。
- **扫描 PDF 没有文字**：这是需要 OCR 的材料。可在授权的 OCR 工具中处理后，把可核对的结果放回订单；v0.1 没有内置在线 OCR。
- **旧 `.doc` / `.xls`**：先通过办公软件另存为 `.docx` / `.xlsx`，再导入。
- **数据或样张更新后命令要求重新确认**：运行 `status` 查看当前确认有效性，按变更范围检查并记录新的真实确认。
- **AI 声称无法访问文件**：采用 `docs/desktop-ai.md` 的上传/手动路线，不需要反复要求同一个环境执行它没有的工具。

参考：[Python 虚拟环境](https://docs.python.org/3/library/venv.html)、[python-pptx 文档](https://python-pptx.readthedocs.io/en/latest/)、[OpenAI Skills 文档](https://learn.chatgpt.com/docs/build-skills)。
