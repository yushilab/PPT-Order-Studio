# 可选设计引擎与样张切换

项目保留内置生成器，并提供可选的 PPTAgent Skill 接入。默认使用 `builtin`；选择 `pptagent` 后，AI 宿主负责设计 HTML 页面，PPTAgent 负责渲染、可编辑 PPTX 转换和视觉审阅证据，本项目继续管理订单、客户确认、当前文件和交付。

切换设计方式会创建新一轮设计，保留上一轮样张和文件。客户确认始终对应当前引擎、设计轮次与实际文件，不会把旧方案的认可自动套到新方案。

下文 `python` 指当前项目 `.venv` 的 Python。Windows 为 `.venv/Scripts/python.exe`；macOS/Linux 为 `.venv/bin/python`。CLI 参数以 `python -m pptstudio --help` 及子命令帮助为准。

## 选择默认方式

查看或调整本机这个项目的新订单默认值：

```bash
python -m pptstudio configure
python -m pptstudio configure --default-engine builtin
```

希望新订单优先使用 PPTAgent 时：

```bash
python -m pptstudio configure --default-engine pptagent
```

默认设置保存在被 Git 忽略的 `.pptstudio/config.json`，不修改其他电脑或现有订单。新克隆的项目没有此配置时使用 `builtin`。选择 PPTAgent 不会自动安装运行环境、调用模型或回退为内置版式；运行环境未就绪时会明确报告。

单个订单可以覆盖默认值：

```bash
python -m pptstudio init orders/client-a --title "年度汇报" --pages 20 --engine pptagent
python -m pptstudio init orders/client-b --title "季度总结" --pages 8 --engine builtin
```

每条 `init` 使用一个空的新目录。继续旧订单先执行 `status`。

## PPTAgent 需要什么环境

官方 Skill 源码固定在仓库的 `third_party/pptagent/`，来源版本和许可证见该目录的 `UPSTREAM.json`、`LICENSE` 以及根目录 `THIRD_PARTY_NOTICES.md`。项目不会默认把上游宽泛的 PPTAgent Skill 注册到用户全局；只在选中它的订单中按需读取。

本项目的两个路由 Skill 可按需安装到当前仓库的 `.agents/skills/`：

```bash
python scripts/install_skill.py --skill all
```

`--skill workflow` 或 `--skill design` 可只安装其中一个。该命令不注册全局 Skill，也不安装上游运行环境；不支持项目 Skill 自动发现的宿主，直接读取 `AI_START_HERE.md` 即可。

基础订单流程和 `builtin` 不需要额外安装。PPTAgent 的可选运行环境需要 Linux/WSL 或 macOS、Python 3.11+、Node/npm、LibreOffice，以及其转换、浏览器和渲染依赖。原生 Windows 下的环境检查会说明需要 WSL；本项目不会替用户安装 WSL 或系统软件。

先检查：

```bash
python -m pptstudio design-doctor
python scripts/setup_pptagent.py --check
```

在官方支持的系统中，按检查结果补齐系统依赖，再主动执行可选安装：

```bash
python scripts/setup_pptagent.py --install
```

PPTAgent 使用 `third_party/pptagent/.venv` 运行环境，不把其全部依赖加入项目基础 `.venv`。安装器不会安装系统软件。在 WSL 中执行时，使用 WSL 内的解释器与实际路径，并访问同一订单文件；不要将 Windows 路径原样当作 Linux 路径。

宿主 AI 需要能够读写文件、运行命令和检查页面图片。只有聊天或上传能力的应用仍需操作者代为运行命令。纯文本宿主若配置上游的外部视觉审阅服务，会涉及单独的接口、凭据和费用；本项目不会自动获取或填写密钥。

## 用 PPTAgent 做一轮样张

资料分析和逐页大纲沿用原流程。客户确认大纲后，确保订单选择了 `pptagent`，再执行：

```bash
python -m pptstudio design orders/client-a
python -m pptstudio sample orders/client-a --slides S01,S06,S12
```

这里 `S01,S06,S12` 必须是实际大纲中的页面。建议选择 3～5 页覆盖正文、图表和图片等代表需求。

PPTAgent 可使用 `layout: custom` 自由排版，但仍应填写标题、核心信息和来源引用等大纲字段。它不要求把自由 HTML 页面强行填成内置版式的指标、正文或图表字段；本项目仍校验内容、来源和页面选择。

PPTAgent 模式下，`sample` 返回 `status: needs_authoring`、本轮 `workspace` 和交接说明。这个状态表示材料已准备好，尚未生成可交付样张。AI 接下来：

1. 读取本轮交接材料及项目 `skills/ppt-order-design/SKILL.md`。
2. 按路由读取 `third_party/pptagent/SKILL.md` 和必要参考文件，使用该组件的解释器。
3. 在本轮工作区编写 HTML/CSS 页面，执行上游渲染、逐页审阅、转换、整稿审阅和 `finalize`。
4. 核对 `answer.pptx` 与 `final-report.json`，再将实际结果导入本项目。

导入时替换为本次返回的真实工作区：

```bash
python -m pptstudio design-import orders/client-a --workspace "本次返回的实际workspace路径"
python -m pptstudio qa orders/client-a --sample
```

导入会核对当前设计轮次、订单输入、PPTX 哈希、页数、比例和上游的审阅/构建证据。只手写一个 `complete: true` 报告不能通过；来源或证据变化后也应重新生成和检查。不要手改任一工具管理的状态或证据文件。

导入后继续保留该轮工作区中的 HTML、资源、渲染及审阅文件；当前文件的后续检查仍会核验这些证据。删除或修改它们会使已导入版本失效；跨电脑继续时应连同订单工作区一起复制。

导入不是客户确认。你审阅实际样张并取得客户认可后，才记录：

```bash
python -m pptstudio approve orders/client-a --scope design --by "操作者" --client-confirmed
```

`--draft` 仅用于试作。草稿不能代替正式设计确认或最终交付。

## 第一版不满意时换一种方式

例如 PPTAgent 样张不满意，改用内置方式：

```bash
python -m pptstudio design orders/client-a --engine builtin --label "第二轮，改用内置版式"
python -m pptstudio sample orders/client-a --slides S01,S06,S12
```

反过来，从内置方式改用 PPTAgent：

```bash
python -m pptstudio design orders/client-a --engine pptagent --label "第二轮，尝试自由排版"
python -m pptstudio sample orders/client-a --slides S01,S06,S12
```

明确设置 `--engine` 会开始一轮新设计，即使选择的引擎与当前相同。上轮内容和样式快照、样张、全稿及相关确认会归档；新一轮不沿用旧的设计确认和最终验收。仅改变引擎而未改变内容时，大纲确认可继续有效；改动需求、事实、来源或页面核心任务后，仍需按 `status` 重新核对。

切回 `builtin` 时，先将 `layout: custom` 转成支持的内置版式，并确保页面详细字段满足其布局要求；自由 HTML 设计不等于内置布局的正文、指标或图表字段已经完整。

查看轮次并恢复一轮历史方案：

```bash
python -m pptstudio design orders/client-a
python -m pptstudio design orders/client-a --restore "实际历史轮次ID"
```

恢复会切回该轮保存的页面和样式快照，并核验其文件及确认。只有当前大纲、事实和来源与归档时匹配，才能直接恢复。新一轮的工作也先归档。恢复后读取 `status`，不凭记忆认为旧确认仍然有效。

已有人工 `baseline` 时，会阻止切换和恢复，以保护手工精修。继续基于人工稿修改并重新登记；需要大幅重建时另建订单，保留旧订单。

## 确认后完成全稿

设计确认有效后：

```bash
python -m pptstudio build orders/client-a
```

`builtin` 直接生成完整 PPTX；`pptagent` 再次返回全稿的 `needs_authoring` 工作区。让 AI 在新工作区沿用已确认样张的视觉规范和组件，完成全部页面、上游审阅和转换，再 `design-import` 该次全稿工作区。

每次交接均应核对当前内容、页数和来源。全部页面完成后，对本项目登记的当前全稿执行 `qa`，在目标 PowerPoint/WPS 中核查字体、中文断行、图片裁剪和可编辑性。有人工精修时先用 `baseline` 登记实际文件，再重新 `qa`；没有精修可直接保留导入稿。取得客户最终认可并完成目标软件检查后：

```bash
python -m pptstudio qa orders/client-a
python -m pptstudio approve orders/client-a --scope final --by "操作者" --client-confirmed --visual-reviewed
python -m pptstudio package orders/client-a
```

包内版本摘要会记录实际设计引擎和轮次，便于定位交付的是哪一版。

## 给 AI 的简短提示

启用：

```text
本订单使用 PPTAgent 设计。请先检查当前引擎和运行环境，按项目设计 Skill 准备样张。
只读取本轮交接材料；由你完成页面设计，并实际查看渲染结果，再导入通过检查的样张。
客户确认之前停在样张评审。
```

切换：

```text
第一轮样张不满意。请保留上一轮，改用 builtin（或 pptagent）开始新一轮样张。
保持已确认的大纲，报告实际引擎、轮次、文件和需要重新确认的内容。
```

控制消耗：将设计探索集中在代表样张；确认后复用视觉规范和组件。只加载当前轮次和当前批次的内容，优先修有问题的页面。字符预算不是准确 Token 预算，渲染检查、图片理解及可选视觉服务也要按实际用量记录。

## 来源与验证范围

上游固定版本为 `833cda553b343be0e486a93b0b57cac962cdd566`，官方来源为 [PPTAgent 仓库](https://github.com/icip-cas/PPTAgent/tree/833cda553b343be0e486a93b0b57cac962cdd566/skills/pptagent)。Skill 本身采用 MIT 许可证；源码和版权声明随可选组件保留。

本项目的适配验证与完整的上游视觉生成验证分别记录。原生 Windows 下的协议或测试通过，不代表已经在 WSL/macOS 完成 HTML 渲染、转换或实际模型设计；以 `design-doctor`、实际执行输出和页面检查为准。
