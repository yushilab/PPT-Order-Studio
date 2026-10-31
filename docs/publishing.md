# 发布开源仓库与后续计划

项目仓库：[yushilab/PPT-Order-Studio](https://github.com/yushilab/PPT-Order-Studio)。以下步骤用于首次推送或后续维护；仓库的访问权限由拥有者在 GitHub 管理。

## 发布前

运行测试和示例检查。确认暂存文件中没有 `.venv`、真实订单、私人材料、密钥、手工精修客户稿或临时导出文件。`orders/` 默认忽略；如果将客户材料放在其他目录，操作者仍需检查。

若代码包尚未初始化 Git，可在项目根目录执行：

```bash
git init
git add .
git status --short
```

审阅暂存清单后，再创建提交并推送到你新建的空仓库：

```bash
git commit -m "Initial open-source release"
git branch -M main
git remote add origin https://github.com/yushilab/PPT-Order-Studio.git
git push -u origin main
```

若远程 origin 已配置，先检查地址；重复添加会报错。托管服务的登录、公开范围和仓库创建由拥有账号的人完成或明确授权代理完成。已存在 Git 仓库时先检查当前分支和 remote，避免重复初始化或覆盖现有历史。

README 已提供实际克隆地址。新用户可以 `git clone` 或从仓库页面下载源码 ZIP，再按安装文档创建环境。正式 Release 和版本标签按需要另行发布。

## v0.2 已提供的工作方式

本地 CLI 与 JSON 是稳定接口；AI 在会话中读取材料、输出内容，工具执行确定性操作。核心无需云端模型服务；模型 API、桌面应用权限和外部服务均未被项目自动接管。

可选 PPTAgent 源码随仓库和 source 包分发并保留 MIT 版权，普通 wheel 只提供基础流程，PPTAgent 需使用完整仓库。它默认关闭，有独立环境、订单轮次与导入接口；详见 [设计引擎指南](design-engines.md)。发布检查须同时排除 `third_party/pptagent/` 下的虚拟环境、node_modules、runtime-status.json、私人 config.yaml 和 .env；保留可分发的 .env.example。

## 可逐步增加的能力

以下是后续方向，不是本版已完成功能：

- 更多组件、客户品牌主题和原生表格页型。
- 可配置的本地 OCR，保留识别置信度与复核位置。
- 模型 API 适配器、实测 Token 和成本预算上限。
- 页面预览与反馈界面、订单看板。
- 人工修改与构建源的同步工具。
- 更细的视觉回归检查和目标软件测试矩阵。

添加在线模型接口前，应定义数据发送范围、密钥保存、计费和中断机制；不要让可选联网能力成为本地基础流程的隐式依赖。
