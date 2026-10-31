"""CLI/core integration; upstream-format evidence is explicitly synthetic.

No model, browser or presentation renderer runs here. These tests verify state
transitions and delivery gates, not the aesthetic quality of PPTAgent output.
"""
import json
import shutil
from pathlib import Path

import pytest

from pptstudio import core
from pptstudio.cli import main
from pptstudio.design import active_design, switch_design
from test_pptagent_bridge import fixture_result


@pytest.fixture
def order(tmp_path):
    root = tmp_path / "order"
    core.init_order(root, "Synthetic integration test", 3, engine="pptagent")
    core.write_json(root / "deck.json", {"schema_version": 1, "slides": [
        {"id": f"S{i:02d}", "title": f"Page {i}", "message": "Synthetic test only",
         "layout": "custom", "source_refs": []} for i in range(1, 4)
    ]})
    return root


def confirmed_sample(order):
    core.approve(order, "plan", "Test operator", confirmed=True)
    _, workspace = fixture_result(order)
    imported = core.import_design(order, workspace)
    assert imported["qa"]["passed"]
    core.approve(order, "design", "Test operator", confirmed=True)
    return imported, workspace


def test_cli_defaults_and_order_override_do_not_change_existing_orders(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="ppt-order-studio"\n', encoding="utf-8")
    monkeypatch.chdir(project)
    assert main(["configure"]) == 0
    assert "builtin" in capsys.readouterr().out
    first = project / "orders" / "first"
    assert main(["init", str(first), "--title", "One", "--pages", "3"]) == 0
    assert active_design(first)["engine"] == "builtin"
    assert main(["configure", "--default-engine", "pptagent"]) == 0
    second = project / "orders" / "second"
    assert main(["init", str(second), "--title", "Two", "--pages", "3"]) == 0
    assert active_design(second)["engine"] == "pptagent"
    third = project / "orders" / "third"
    assert main(["init", str(third), "--title", "Three", "--pages", "3", "--engine", "builtin"]) == 0
    assert active_design(third)["engine"] == "builtin"
    assert active_design(first)["engine"] == "builtin"


def test_external_cli_sample_is_handoff_not_generated_deck(order, capsys):
    assert main(["sample", str(order), "--slides", "S01,S03"]) == 2
    core.approve(order, "plan", "Test operator", confirmed=True)
    assert main(["sample", str(order), "--slides", "S01,S03"]) == 0
    response = json.loads(capsys.readouterr().out)
    assert response["status"] == "needs_authoring"
    assert not (Path(response["workspace"]) / "answer.pptx").exists()
    assert not core.read_json(order / "state.json")["artifacts"]
    assert not core.approval_valid(order, "design")
    with pytest.raises(core.WorkflowError, match="design"):
        core.build(order)
    assert main(["design-import", str(order), "--workspace", response["workspace"]]) == 2


def test_synthetic_external_sample_full_delivery_and_stale_proof(order, capsys):
    sample, sample_workspace = confirmed_sample(order)
    sample_id = sample["sha256"]
    _, full_workspace = fixture_result(order, stage="full")
    assert main(["design-import", str(order), "--workspace", str(full_workspace)]) == 0
    response = json.loads(capsys.readouterr().out)
    assert response["qa"]["passed"] and not response["draft"]
    assert response["customer_approval_created"] is False
    assert core.read_json(order / "state.json")["artifacts"]["sample"]["sha256"] == sample_id
    assert core.approval_valid(order, "design")
    assert (sample_workspace / "slides" / "slide01.html").exists()
    core.approve(order, "final", "Test operator", confirmed=True, visual_reviewed=True)
    result = core.package(order)
    assert Path(result["zip"]).is_file()
    (full_workspace / "slides" / "slide01.html").write_text("changed after import", encoding="utf-8")
    assert not core.approval_valid(order, "final")
    with pytest.raises(ValueError):
        core.package(order)


def test_imported_draft_cannot_be_promoted_by_renaming_or_archiving(order, tmp_path):
    confirmed_sample(order)
    _, workspace = fixture_result(order, stage="full", draft=True)
    imported = core.import_design(order, workspace)
    assert imported["draft"] and imported["qa"]["passed"]
    renamed = tmp_path / "renamed.pptx"
    shutil.copy2(order / imported["path"], renamed)
    with pytest.raises(core.WorkflowError, match="草稿"):
        core.set_baseline(order, renamed, "Cannot promote a draft")
    switch_design(order, "pptagent", "New test round")
    confirmed_sample(order)
    with pytest.raises(core.WorkflowError, match="草稿"):
        core.set_baseline(order, renamed, "Cannot promote an archived draft")


def test_switch_clears_design_and_full_but_preserves_outline(order, capsys):
    sample, _ = confirmed_sample(order)
    previous = active_design(order)["attempt_id"]
    assert main(["design", str(order), "--engine", "builtin", "--label", "Alternative"]) == 0
    assert (order / sample["path"]).is_file()
    state = core.read_json(order / "state.json")
    assert state["artifacts"] == {}
    assert core.approval_valid(order, "plan")
    assert not core.approval_valid(order, "design")
    assert main(["design", str(order), "--restore", previous]) == 0
    assert core.approval_valid(order, "design")
    assert active_design(order)["engine"] == "pptagent"
    assert main(["design", str(order), "--label", "Missing engine"]) == 2


def test_external_full_import_cannot_override_manual_baseline(order):
    confirmed_sample(order)
    _, workspace = fixture_result(order, stage="full")
    full = core.import_design(order, workspace)
    core.set_baseline(order, order / full["path"], "Synthetic manual baseline")
    with pytest.raises(core.WorkflowError, match="人工基准"):
        core.import_design(order, workspace)
    with pytest.raises(core.WorkflowError, match="人工基准"):
        switch_design(order, "builtin")


def test_verified_formal_file_can_match_an_earlier_draft_hash(order):
    confirmed_sample(order)
    _, draft_workspace = fixture_result(order, stage="full", draft=True)
    core.import_design(order, draft_workspace)
    _, formal_workspace = fixture_result(order, stage="full")
    # Simulate a deterministic converter: an unchanged design can produce the
    # exact same PPTX bytes in a later formal request. Evidence stays current.
    shutil.copy2(draft_workspace / "answer.pptx", formal_workspace / "answer.pptx")
    checksum = core.file_hash(formal_workspace / "answer.pptx")
    upstream = core.read_json(formal_workspace / "workspace-state.json")
    upstream["build"]["artifact_sha256"] = checksum
    upstream["renders"]["deck"]["inputs"]["artifact_sha256"] = checksum
    upstream["reviews"]["deck"]["render"]["inputs"]["artifact_sha256"] = checksum
    core.write_json(formal_workspace / "workspace-state.json", upstream)
    report = core.read_json(formal_workspace / "final-report.json")
    report["artifact_sha256"] = checksum
    core.write_json(formal_workspace / "final-report.json", report)
    formal = core.import_design(order, formal_workspace)
    assert formal["draft"] is False and formal["qa"]["passed"]
    baseline = core.set_baseline(order, order / formal["path"], "Formal provenance takes precedence")
    assert baseline["draft"] is False
