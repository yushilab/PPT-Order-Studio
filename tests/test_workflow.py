import json
import zipfile
from importlib.resources import files

import pytest

from pptstudio import core
from pptstudio.cli import main
from pptstudio.ingest import ingest_order


@pytest.fixture
def order(tmp_path):
    root = tmp_path / "订单 空格"
    core.init_order(root, "虚构测试项目", 5)
    (root / "sources" / "说明.md").write_text("# 测试资料\n\n本例数字仅供测试。", encoding="utf-8")
    manifest = ingest_order(root)
    data = files("pptstudio").joinpath("data", "demo-deck.json")
    deck = json.loads(data.read_text(encoding="utf-8"))
    for slide in deck["slides"]:
        slide["source_refs"] = [manifest["files"][0]["id"]]
    core.write_json(root / "deck.json", deck)
    return root


def confirmed_design(order):
    core.approve(order, "plan", "test operator", confirmed=True)
    core.build(order, ["S01", "S03", "S04"])
    assert core.qa_sample(order)["passed"]
    core.approve(order, "design", "test operator", confirmed=True)


def test_existing_directory_never_overwritten(tmp_path):
    (tmp_path / "precious.txt").write_text("keep")
    with pytest.raises(core.WorkflowError, match="非空"):
        core.init_order(tmp_path, "project", 5)
    assert (tmp_path / "precious.txt").read_text() == "keep"


def test_build_requires_both_real_approval_records(order):
    with pytest.raises(core.WorkflowError, match="plan"):
        core.build(order)
    core.approve(order, "plan", "operator", confirmed=True)
    with pytest.raises(core.WorkflowError, match="design"):
        core.build(order)


def test_approval_requires_explicit_attestation(order):
    with pytest.raises(core.WorkflowError, match="client-confirmed"):
        core.approve(order, "plan", "operator")
    assert not core.approval_valid(order, "plan")


def test_draft_cannot_be_design_confirmation(order):
    core.approve(order, "plan", "operator", confirmed=True)
    core.build(order, ["S01", "S03", "S04"], draft=True)
    with pytest.raises(core.WorkflowError, match="草稿"):
        core.approve(order, "design", "operator", confirmed=True)


def test_outline_and_representative_sample_allow_unfilled_other_pages(order):
    data = core.read_json(order / "deck.json")
    data["slides"][1].pop("body")
    core.write_json(order / "deck.json", data)
    assert any(i["severity"] == "error" for i in core.validate(order))
    assert not any(i["severity"] == "error" for i in core.validate(order, outline=True))
    confirmed_design(order)
    with pytest.raises(core.WorkflowError, match="校验"):
        core.build(order)


def test_detail_edit_keeps_outline_but_title_edit_invalidates(order):
    core.approve(order, "plan", "operator", confirmed=True)
    deck = core.read_json(order / "deck.json")
    deck["slides"][1]["body"] = ["在已确认的结论下补充具体说明。"]
    core.write_json(order / "deck.json", deck)
    assert core.approval_valid(order, "plan")
    deck["slides"][1]["title"] = "新的叙事重点"
    core.write_json(order / "deck.json", deck)
    assert not core.approval_valid(order, "plan")


def test_style_change_cannot_confirm_old_sample(order):
    core.approve(order, "plan", "operator", confirmed=True)
    core.build(order, ["S01", "S03", "S04"])
    core.qa_sample(order)
    style = core.read_json(order / "style.json")
    style["primary"] = "442222"
    core.write_json(order / "style.json", style)
    with pytest.raises(core.WorkflowError, match="输入已变化"):
        core.approve(order, "design", "operator", confirmed=True)


def test_non_sample_detail_does_not_invalidate_design(order):
    confirmed_design(order)
    deck = core.read_json(order / "deck.json")
    deck["slides"][1]["body"] = ["新正文，保留本页结论。"]
    core.write_json(order / "deck.json", deck)
    assert core.approval_valid(order, "plan")
    assert core.approval_valid(order, "design")


def test_changed_sources_block_before_reingest(order):
    confirmed_design(order)
    (order / "sources" / "说明.md").write_text("changed", encoding="utf-8")
    assert not core.approval_valid(order, "plan")
    with pytest.raises(core.WorkflowError, match="ingest"):
        core.build(order)
    ingest_order(order)
    assert not core.approval_valid(order, "plan")


def test_context_is_bounded_and_points_back_to_sources(order):
    source = order / "sources" / "说明.md"
    source.write_text("事实与单位。" * 20000, encoding="utf-8")
    ingest_order(order)
    result = core.make_context(order, "build", ["S03"], max_chars=4000)
    text = (order / "contexts" / "build.md").read_text(encoding="utf-8")
    assert len(text) <= 4000
    assert "source" in text and result["token_count"] is None
    with pytest.raises(core.WorkflowError, match="不存在"):
        core.make_context(order, "build", ["S999"])


def test_impact_follows_fact_to_slide(order):
    sid = core.read_json(order / "sources.json")["files"][0]["id"]
    core.write_json(order / "facts.json", {"facts": [{"id": "F001", "text": "测试事实", "source_refs": [sid + "#line1"]}]})
    deck = core.read_json(order / "deck.json")
    deck["slides"][2]["source_refs"] = ["F001"]
    core.write_json(order / "deck.json", deck)
    assert "S03" in core.impact(order, sid)["slide_ids"]
    assert not any(i["severity"] == "error" for i in core.validate(order))


def test_delivery_requires_qa_and_visual_review_then_packages_only_final(order):
    confirmed_design(order)
    core.build(order)
    with pytest.raises(core.WorkflowError, match="visual-reviewed"):
        core.approve(order, "final", "operator", confirmed=True)
    with pytest.raises(core.WorkflowError, match="结构检查"):
        core.approve(order, "final", "operator", confirmed=True, visual_reviewed=True)
    assert core.qa(order)["passed"]
    core.approve(order, "final", "operator", confirmed=True, visual_reviewed=True)
    result = core.package(order)
    with zipfile.ZipFile(result["zip"]) as bundle:
        assert set(bundle.namelist()) == {"final.pptx", "manifest.json"}


def test_model_edit_makes_previous_full_pptx_stale(order):
    confirmed_design(order)
    core.build(order)
    deck = core.read_json(order / "deck.json")
    deck["slides"][1]["body"] = ["修订细节"]
    core.write_json(order / "deck.json", deck)
    with pytest.raises(core.WorkflowError, match="过期"):
        core.qa(order)


def test_manual_baseline_protects_refinements(order):
    confirmed_design(order)
    record = core.build(order)
    baseline = core.set_baseline(order, order / record["path"], "测试人工精修登记")
    assert core.current_artifact(order)[0]["sha256"] == baseline["sha256"]
    with pytest.raises(core.WorkflowError, match="人工作业基准"):
        core.build(order)
    assert core.qa(order)["passed"]


def test_draft_metadata_cannot_be_laundered_as_manual_baseline(order):
    confirmed_design(order)
    record = core.build(order, draft=True)
    with pytest.raises(core.WorkflowError, match="草稿标记"):
        core.set_baseline(order, order / record["path"], "must reject")


def test_tampered_artifact_is_not_accepted(order):
    confirmed_design(order)
    record = core.build(order)
    with (order / record["path"]).open("ab") as handle:
        handle.write(b"changed")
    with pytest.raises(core.WorkflowError, match="文件已变化"):
        core.qa(order)


def test_usage_unknown_and_invalid_values(order):
    result = core.log_usage(order, "sample", provider="desktop", note="应用未提供精确用量")
    assert result.get("input_tokens") is None
    with pytest.raises(core.WorkflowError):
        core.log_usage(order, "sample", cost=float("nan"))
    with pytest.raises(core.WorkflowError):
        core.log_usage(order, "sample", input_tokens=10, cached_tokens=11)


def test_feedback_is_pending_not_automatically_applied(order):
    before = core.file_hash(order / "deck.json")
    record = core.feedback(order, "第 2 页缩短正文", "local", ["S02"])
    assert record["status"] == "pending"
    assert core.file_hash(order / "deck.json") == before


def test_cli_demo_creates_no_approval_and_returns_success(tmp_path, capsys):
    target = tmp_path / "portable example"
    assert main(["demo", str(target)]) == 0
    assert not core.read_json(target / "state.json")["approvals"]
    assert main(["package", str(target)]) == 2
    assert main(["status", str(target)]) == 0


def test_context_rejects_silent_truncation_of_core_records(order):
    deck = core.read_json(order / "deck.json")
    deck["slides"][1]["body"] = ["说明" * 6000]
    core.write_json(order / "deck.json", deck)
    with pytest.raises(core.WorkflowError, match="核心资料已超过"):
        core.make_context(order, "build", ["S02"], 2000)
