# 实测记录

日期：2026-10-26。

## v0.2 可选设计接入

- Windows 本地运行：`110 passed, 1 skipped`；仍跳过需要符号链接权限的测试。包括项目默认/订单覆盖、轮次归档/恢复、独立旧版指纹兼容、样张到交付、证据变更和外部草稿限制。
- PPTAgent 固定版本完整 Skill 源码与 MIT 许可随仓库保留，按 Git blob 原始字节及摘要校验；未执行上游安装脚本或全局注册。
- `design-doctor` 与 `setup_pptagent.py --check` 只读检查，当前原生 Windows 正确显示不支持直接运行、未就绪。
- 外部导入及交付测试使用真实 PPTX ZIP 和明确标记的合成上游证据，验证协议及状态约束；没有调用模型、浏览器或 LibreOffice，不能作为视觉质量或真实转换效果的证据。
- 没有安装 WSL、PPTAgent 运行依赖或外部视觉服务，也没有在本环境完成实际 HTML→PPTX 全链路。使用者须在 WSL/Linux 或 macOS 安装后完成真实样张和目标软件检查。

## v0.1 基础流程

## 已执行

- Windows、Python 3.13.9 的本地虚拟环境安装与 editable 安装通过。
- `pytest`：53 passed、1 skipped；跳过项需要当前会话没有的 Windows 符号链接创建权限。
- 五页虚构订单可生成完整草稿与三页样张，原生文字和可编辑图表存在于 PPTX。
- 缓存、来源变更、内容/风格版本、审批、草稿限制、人工基准保护、结构检查、最终打包等自动测试通过。
- 使用本机 PowerPoint 导出示例 PDF；五页转 PNG 后逐页检查，未见文字裁切、遮挡或中文缺字。
- 当前受限执行会话直接访问 PowerPoint 曾返回 COM 不可用；在有权限访问本机 Office 的会话中成功。其他机器需按实际权限测试或手动导出。
- 独立代理按 AI_START_HERE 和自有 Skill，在新订单中整理资料、建立来源和五页大纲，并正常停在客户确认前，没有生成虚假审批。
- Skill 格式校验、相对文档链接检查、wheel/source 包构建通过。

## 验证范围

自动测试及示例不是对任意客户资料、复杂模板、字体或 Office 版本的效果保证。新订单仍需检查事实和实际渲染。当前没有真实客户端的 ChatGPT/豆包/Gemini 端到端自动操控测试，文档按文件与命令能力提供不同使用方式。

仓库配置了 Windows/Linux、Python 3.10/3.13 的 GitHub Actions；配置存在不代表这些远端任务已经运行。macOS 安装指引尚未在本次环境实际执行。

`requirements-tested.txt` 记录本次主要运行依赖版本，正常安装入口仍是 pyproject 和 bootstrap。
