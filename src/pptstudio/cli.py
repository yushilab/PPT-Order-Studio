"""Small auditable command surface, suitable for agents or manual execution."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, core


def ids(value):
    return [item.strip() for item in value.split(",") if item.strip()] if value else None


def parser():
    p = argparse.ArgumentParser(prog="pptstudio", description="本地 PPT 接单工作流；AI 规划，脚本执行，无需模型 API。")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="检查 Python、依赖和可选渲染工具")
    doctor.add_argument("--json", action="store_true", help="输出机器可读 JSON（默认即 JSON）")
    configure = sub.add_parser("configure", help="查看或设置当前项目新订单的默认设计引擎")
    configure.add_argument("--default-engine", choices=["builtin", "pptagent"])
    sub.add_parser("design-doctor", help="检查可选 PPTAgent 源码与运行环境；不安装工具")
    for name, help_text in {
        "init": "创建订单", "ingest": "增量提取 sources/", "source": "按来源 ID 回查原文", "context": "生成有界 AI 材料包",
        "status": "查看确认有效性和当前文件", "validate": "验证内容及设计数据", "sample": "生成 1～5 页样张",
        "build": "按已确认规范生成全稿", "approve": "依据客户明确意见登记确认", "qa": "检查当前 PPTX 的结构",
        "render": "用可选 Office/LibreOffice 导出 PDF", "baseline": "登记人工精修稿", "feedback": "登记反馈及处理范围",
        "impact": "查询来源影响的事实和页面", "usage": "记录可获取的用量或费用", "package": "打包已验收的当前文件",
        "demo": "生成虚构的五页草稿示例，不伪造审批", "design": "选择、查看或恢复设计方案",
        "design-import": "导入已完成审阅和转换的 PPTAgent 产物"}.items():
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("order", type=Path)
        if name == "init":
            cmd.add_argument("--title", required=True)
            cmd.add_argument("--pages", required=True, type=int)
            cmd.add_argument("--audience", default="")
            cmd.add_argument("--requirements", default="")
            cmd.add_argument("--engine", choices=["builtin", "pptagent"])
        elif name == "design":
            group = cmd.add_mutually_exclusive_group()
            group.add_argument("--engine", choices=["builtin", "pptagent"])
            group.add_argument("--restore", metavar="ATTEMPT_ID")
            cmd.add_argument("--label", default="")
        elif name == "design-import":
            cmd.add_argument("--workspace", required=True, type=Path)
        elif name == "source":
            cmd.add_argument("source_id")
            cmd.add_argument("--start", type=int, default=0)
            cmd.add_argument("--limit", type=int, default=6000)
        elif name == "validate":
            cmd.add_argument("--outline", action="store_true", help="只核对大纲，允许尚未填入详细正文/图表数据")
        elif name == "context":
            cmd.add_argument("--stage", choices=["analyze", "plan", "sample", "build", "revise"], required=True)
            cmd.add_argument("--slides")
            cmd.add_argument("--max-chars", type=int, default=24000)
        elif name in {"sample", "build"}:
            cmd.add_argument("--draft", action="store_true", help="草稿可绕过确认；不能用于正式确认或交付")
            if name == "sample":
                cmd.add_argument("--slides", required=True)
        elif name == "approve":
            cmd.add_argument("--scope", choices=["plan", "design", "final"], required=True)
            cmd.add_argument("--by", required=True)
            cmd.add_argument("--client-confirmed", action="store_true")
            cmd.add_argument("--visual-reviewed", action="store_true")
            cmd.add_argument("--note", default="")
        elif name in {"qa", "render"}:
            cmd.add_argument("--sample", action="store_true")
            if name == "render":
                cmd.add_argument("--backend", choices=["auto", "libreoffice", "powerpoint"], default="auto")
        elif name == "baseline":
            cmd.add_argument("--pptx", type=Path, required=True)
            cmd.add_argument("--note", required=True)
        elif name == "feedback":
            cmd.add_argument("--text", required=True)
            cmd.add_argument("--kind", choices=["local", "data", "style", "structure"], required=True)
            cmd.add_argument("--slides")
        elif name == "impact":
            cmd.add_argument("source_id")
        elif name == "usage":
            cmd.add_argument("--stage", required=True)
            for flag in ("input-tokens", "output-tokens", "cached-tokens"):
                cmd.add_argument("--" + flag, type=int)
            cmd.add_argument("--cost", type=float)
            for flag, default in (("provider", "unknown"), ("model", "unknown"), ("currency", "USD"), ("note", "")):
                cmd.add_argument("--" + flag, default=default)
        elif name == "package":
            cmd.add_argument("--pdf", type=Path)
    return p


def demo(order: Path):
    from importlib.resources import files
    from .ingest import ingest_order
    core.init_order(order, "交通文旅融合 · 示例成果汇报", 5, "项目评审人员", "虚构演示数据；用于验证流程，不代表真实客户材料。", engine="builtin")
    order = order.resolve()
    data = files("pptstudio").joinpath("data")
    for name in ("demo-source.md", "demo-data.csv"):
        (order / "sources" / name).write_text(data.joinpath(name).read_text(encoding="utf-8"), encoding="utf-8")
    manifest = ingest_order(order)
    refs = [f["id"] for f in manifest["files"]]
    deck = json.loads(data.joinpath("demo-deck.json").read_text(encoding="utf-8"))
    for slide in deck["slides"]:
        slide["source_refs"] = refs
    core.write_json(order / "deck.json", deck)
    result = core.build(order, draft=True)
    core.build(order, slide_ids=["S01", "S03", "S04"], draft=True)
    check = core.qa(order)
    return {"order": str(order), "draft_pptx": result["path"], "structural_qa_passed": check["passed"],
            "customer_approvals_created": False, "next": "打开草稿检查；真实订单按 AI_START_HERE.md 开始。"}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        cmd = args.command
        result = None
        code = 0
        if cmd == "doctor":
            result = core.doctor()
            code = 0 if result["core_ready"] else 1
        elif cmd == "configure":
            from .design import configure_default, default_engine
            result = configure_default(args.default_engine) if args.default_engine else {"default_design_engine": default_engine()}
        elif cmd == "design-doctor":
            from .pptagent_bridge import runtime_info
            result = runtime_info()
            code = 0 if result.get("ready") else 1
        elif cmd == "init":
            result = core.init_order(args.order, args.title, args.pages, args.audience, args.requirements, engine=args.engine)
        elif cmd == "demo":
            result = demo(args.order)
        else:
            order = core.require_order(args.order)
            if cmd == "ingest":
                from .ingest import ingest_order
                result = ingest_order(order)
            elif cmd == "design":
                from .design import design_history, switch_design, restore_design
                if args.engine:
                    result = switch_design(order, args.engine, args.label)
                elif args.restore:
                    result = restore_design(order, args.restore)
                elif args.label:
                    raise core.WorkflowError("--label 须与 --engine 一起使用。")
                else:
                    result = design_history(order)
            elif cmd == "design-import":
                result = core.import_design(order, args.workspace)
                code = 0 if result["qa"]["passed"] else 1
            elif cmd == "source":
                from .ingest import source_excerpt
                print(source_excerpt(order, args.source_id, args.start, args.limit))
                return 0
            elif cmd == "context":
                result = core.make_context(order, args.stage, ids(args.slides), args.max_chars)
            elif cmd == "validate":
                issues = core.validate(order, outline=args.outline)
                result = {"passed": not any(x["severity"] == "error" for x in issues), "issues": issues}
                code = 0 if result["passed"] else 1
            elif cmd == "status":
                result = core.status(order)
            elif cmd in {"sample", "build"}:
                result = core.build(order, ids(args.slides) if cmd == "sample" else None, args.draft)
                if cmd == "sample" and result.get("status") != "needs_authoring":
                    result = {**result, "qa": core.qa_sample(order)}
            elif cmd == "approve":
                result = core.approve(order, args.scope, args.by, args.client_confirmed, args.visual_reviewed, args.note)
            elif cmd == "qa":
                result = core.qa_sample(order) if args.sample else core.qa(order)
                code = 0 if result["passed"] else 1
            elif cmd == "render":
                from .quality import render_pptx
                core.assert_sources_current(order)
                if args.sample:
                    record = core.read_json(order / "state.json")["artifacts"].get("sample")
                    if not record:
                        raise core.WorkflowError("尚未生成样张。")
                    path = core.artifact_file(order, record)
                else:
                    _, path = core.current_artifact(order)
                result = render_pptx(path, order / "build" / "previews", args.backend)
                code = 0 if result.get("status") in {"ok", "success", "rendered"} else 1
            elif cmd == "baseline":
                result = core.set_baseline(order, args.pptx, args.note)
            elif cmd == "feedback":
                result = core.feedback(order, args.text, args.kind, ids(args.slides))
            elif cmd == "impact":
                result = core.impact(order, args.source_id)
            elif cmd == "usage":
                result = core.log_usage(order, args.stage, **{key: getattr(args, key) for key in (
                    "input_tokens", "output_tokens", "cached_tokens", "cost", "provider", "model", "currency", "note")})
            elif cmd == "package":
                result = core.package(order, args.pdf)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return code
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc), "command": args.command}, ensure_ascii=False), file=sys.stderr)
        return 2
    except ImportError as exc:
        print(json.dumps({"error": f"缺少依赖: {exc}。请运行 bootstrap 或 pip install -e '.[extract]'。"}, ensure_ascii=False), file=sys.stderr)
        return 2
