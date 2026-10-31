# CLI 速查

以下 `python` 统一指本项目 `.venv` 的 Python。可以随时执行 `python -m pptstudio --help` 或对应子命令的 `--help`，真实 CLI 是参数的权威来源。

| 命令 | 作用 |
|---|---|
| `doctor --json` | 检查核心依赖；可选能力缺失不冒充成功 |
| `configure [--default-engine builtin/pptagent]` | 查看/设置本项目的新订单默认设计方式；默认 builtin |
| `design-doctor` | 检查可选 PPTAgent 固定源码与环境，不安装 |
| `init ORDER --title 标题 --pages 20` | 在空目录创建订单 |
| `init ORDER --title 标题 --pages 20 --engine pptagent` | 本订单覆盖默认设计方式 |
| `design ORDER` | 查看当前设计和历史轮次 |
| `design ORDER --engine pptagent --label 第二轮` | 归档当前轮，使用指定方式开始新一轮 |
| `design ORDER --restore 历史轮次ID` | 校验并恢复该轮页面、样式及仍有效的确认 |
| `design-import ORDER --workspace 工作区路径` | 校验并导入 PPTAgent 实际完成的样张/全稿 |
| `ingest ORDER` | 解析 sources/，缓存并报告变化 |
| `source ORDER SOURCE_ID --start 0 --limit 6000` | 分段回查提取原文 |
| `context ORDER --stage analyze --max-chars 24000` | 准备分析材料包；其他阶段为 plan/sample/build/revise |
| `context ORDER --stage build --slides S02,S03` | 只准备当前页面相关资料 |
| `validate ORDER --outline` | 验证逐页大纲，不要求全部详细正文 |
| `validate ORDER` | 验证全部页面和版式内容 |
| `approve ORDER --scope plan --by 姓名 --client-confirmed` | 登记真实的大纲确认 |
| `sample ORDER --slides S01,S06,S12` | 生成已确认大纲对应的正式样张 |
| `qa ORDER --sample` | 检查当前样张结构 |
| `render ORDER --sample` | 尝试把样张导出 PDF；可手动替代 |
| `approve ORDER --scope design --by 姓名 --client-confirmed` | 登记真实的样张确认 |
| `build ORDER` | 在大纲、设计确认有效时生成全稿 |
| `qa ORDER` | 检查当前全稿或人工基准 |
| `render ORDER --backend auto` | 尝试将当前全稿/基准导出 PDF |
| `baseline ORDER --pptx 文件 --note 说明` | 登记人工精修稿，不反向同步 JSON |
| `feedback ORDER --text 意见 --kind local --slides S08` | 保存反馈；分类还包括 data/style/structure |
| `impact ORDER SOURCE_ID` | 根据来源→事实→页面引用查影响范围 |
| `status ORDER` | 查看文件、确认有效性和用量记录覆盖 |
| `usage ORDER --stage sample --provider desktop --note 未提供精确用量` | 记录未知用量；有数据时可传输入/输出/缓存和费用 |
| `approve ORDER --scope final --by 姓名 --client-confirmed --visual-reviewed` | 登记真实视觉检查和最终客户验收 |
| `package ORDER` | 打包实际验收的 PPTX 和版本摘要 |
| `package ORDER --pdf 已核对的最终.pdf` | 同时放入操作者已确认一致的 PDF |
| `demo ORDER` | 创建五页虚构草稿示例，不写入客户确认 |

`sample` 和 `build` 可以加 `--draft` 进行试作，草稿不计入设计确认或正式交付。反馈命令只登记工作，不自动替客户修改内容或关闭意见；完成情况可以通过后续反馈记录、版本与人工修改说明追踪。

PPTAgent 模式下 `sample/build` 返回 `needs_authoring` 交接工作区，由宿主 AI 完成上游设计和审阅后再 `design-import`。环境与分步流程见 [设计引擎指南](design-engines.md)。

命令成功通常返回 0，验证不通过或渲染不可用返回 1，输入或流程错误返回 2。终端输出使用 UTF-8 JSON，`source` 输出纯文本。

项目代码更新尤其是 `deck.py` 组件变化，也会影响文件和设计指纹；需要重新构建并核对样张。不要为了绕过有效性检查手改 state.json。
