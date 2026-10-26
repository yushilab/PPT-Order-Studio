# 订单数据格式

文件使用 UTF-8 JSON。AI 可以直接编辑以下内容文件；由 CLI 管理 `state.json`、构建记录、确认记录和用量日志。大纲完成后运行 `validate --outline`；详细页面完成后运行 `validate`。分析阶段若 deck 仍为空，验证器会报告大纲/页数未完成，这不代表 facts 提取失败。字段以当前 CLI 和代码验证为准。

## brief.json：订单要求

```json
{
  "schema_version": 1,
  "title": "年度经营汇报",
  "audience": "管理层",
  "page_count": 5,
  "requirements": "16:9。重点说明成果、原因与下一步。五页包含封面和结束页。"
}
```

`page_count` 为最终全部页面数。额外业务约定可以写在 `requirements` 中，避免维护第二份内容相互冲突的需求单。

## sources.json：来源目录

`ingest` 自动维护。基本结构：

```json
{
  "schema_version": 1,
  "files": [
    {
      "id": "实际生成的来源ID",
      "path": "sources/客户资料.md",
      "sha256": "实际文件摘要",
      "status": "ok",
      "text_path": "extracted/实际生成的来源ID.md",
      "blocks": [{"locator": "原文位置", "text": "提取内容"}],
      "warnings": []
    }
  ],
  "removed": []
}
```

这是结构示意，不能原样当成真实来源。`id` 由相对文件名生成并保持稳定，文件内容变化通过摘要识别。`locator` 表示段落、表格、工作表单元格、页码等位置，具体取决于文件格式。提取文本缺失和来源删除都应处理，不能默默当成已核实。

## facts.json：事实与口径

```json
{
  "facts": [
    {
      "id": "F001",
      "text": "2025 年营业收入 1200 万元，统计范围为主营业务；原文位置：年度表 B5。",
      "source_refs": ["替换成 sources.json 中的真实ID"]
    }
  ]
}
```

事实文本包含数值、单位、时间和适用范围；`source_refs` 引用真实来源 ID。v0.1 不会凭引用自动核实文字与原文一致，AI 和操作者需要查证。待确认信息可以另外保存为订单内工作笔记，未确认数字不作为确定结论使用。

## style.json：视觉规范

```json
{
  "schema_version": 1,
  "name": "清晰商务",
  "font": "Microsoft YaHei",
  "background": "F7F9FC",
  "foreground": "17342C",
  "primary": "1C6951",
  "accent": "C49A41",
  "muted": "61746D",
  "title_size": 32,
  "body_size": 20,
  "min_font_size": 12
}
```

颜色为六位十六进制，不含 `#`；字号为 pt。字体应按实际机器和客户环境选择，示例字体不代表跨系统都已安装。当前页面比例为 16:9。

## deck.json：逐页内容

```json
{
  "schema_version": 1,
  "slides": [
    {
      "id": "S01",
      "title": "年度经营汇报",
      "message": "回顾经营成果并明确下一阶段行动",
      "layout": "cover",
      "source_refs": [],
      "body": ["2025 年度"]
    }
  ]
}
```

每页的 `id` 稳定且唯一，格式为 S 加 2～4 位数字，例如 S01、S012；插页或调整顺序时保留已有 ID。`title` 是页面标题，`message` 是核心结论；两者都属于规划确认范围。页面 `source_refs` 可以使用真实来源 ID、`来源ID#原文定位说明`，或 `facts.json` 中的事实 ID。事实自己的 `source_refs` 使用真实来源 ID，可附 `#定位说明`。定位后缀帮助回查，不意味着工具已自动核实所引用的位置与结论一致。

| layout | 主要字段 | 适用页面 |
|---|---|---|
| `cover` | `title`、`message`、可选 `body` | 封面和副标题 |
| `bullets` | 非空 `body`：字符串数组 | 观点、说明、行动清单 |
| `metrics` | 1～4 个 `metrics`：含 `label`、`value` | 关键数字和成果 |
| `chart` | 1～12 个 `categories`，1～3 个 `series` | 可编辑数据图表 |
| `image` | 存在的本地 `image`，可选 `caption` | 本地图片配说明 |
| `timeline` | 2～6 个 `events`：含 `year`、`text` | 时间节点或阶段 |
| `closing` | `title`、`message`、可选 `body` | 结束页和行动结语 |

当前布局的文字上限：`title` 100 字符，`message` 240 字符；`body` 最多 6 项、单项 180 字符、合计 650 字符。指标 `label` 最多 60 字符、`value` 24 字符；图表类别名最多 24 字符，每组数值数量与类别数一致且为有限数字；图片 `caption` 最多 350 字符；时间轴 `year` 最多 16 字符、`text` 140 字符。这些是防止明显过载的限制，不是视觉适配保证。

规划阶段可以保留未细化的页面，使用 `validate --outline` 仅检查基础结构。样张验证选定页的完整内容，同时要求全稿页数和页面基础结构正确；正式 `build` 要求所有页面内容符合布局要求。

详细字段示例：

```json
{
  "id": "S03",
  "title": "收入连续增长",
  "message": "三年增长来自主营业务拓展",
  "layout": "chart",
  "source_refs": ["替换成真实来源ID"],
  "chart": {
    "categories": ["2023", "2024", "2025"],
    "series": [{"name": "收入（万元）", "values": [800, 1000, 1200]}]
  },
  "body": ["示例数据为虚构，仅用于展示格式。"]
}
```

```json
{
  "id": "S04",
  "title": "三项关键成果",
  "message": "业务、服务和效率共同改善",
  "layout": "metrics",
  "source_refs": [],
  "metrics": [
    {"label": "服务覆盖区域", "value": "12 个"},
    {"label": "处理时效改善", "value": "20%"}
  ]
}
```

```json
{
  "id": "S05",
  "title": "下一阶段安排",
  "message": "分阶段落实改进措施",
  "layout": "timeline",
  "source_refs": [],
  "events": [
    {"year": "第一阶段", "text": "完成需求核对"},
    {"year": "第二阶段", "text": "上线并验证效果"}
  ]
}
```

以上分离示例需组合为订单要求的完整页数，并替换成实际材料。文字数量、指标和节点数量需要适配现有布局，`validate` 会报告部分边界限制；即使通过也必须视觉检查。

图片路径相对订单目录，例如 `sources/photos/现场.jpg`。仅使用本地订单内素材，CLI 不会自动下载图片 URL，也不会按外部路径读取素材。跨电脑迁移时连同图片一起复制。

## 数据管理边界

- 客户确认不写进内容 JSON，由 `approve` 保存并绑定指纹。
- `state.json` 是执行状态，不由 AI 手工改写以绕过门槛。
- `baseline` 保存实际 PPTX 的版本基准，不反向还原手工修改到 `deck.json`。
- 当前 JSON 是可读的约定格式，不是模型理解质量的保证；来源、事实和设计仍需审阅。
