import hashlib
import json
from pathlib import Path

import pytest

from pptstudio import core
from pptstudio.design import (
    active_design, configure_default, default_engine, design_fingerprint,
    design_history, initialize_design, restore_design, switch_design,
)
from pptstudio.ingest import ingest_order


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "工作目录"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "ppt-order-studio"\n', encoding="utf-8")
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def order(project):
    order = project / "orders" / "example"
    core.init_order(order, "示例", 1)
    initialize_design(order, "builtin")
    core.write_json(order / "deck.json", {"schema_version": 1, "slides": [
        {"id": "S01", "title": "年度汇报", "message": "已确认的核心内容", "layout": "cover", "source_refs": [], "body": ["第一版文案"]}
    ]})
    return order


def confirmed_sample(order):
    core.approve(order, "plan", "synthetic test operator", confirmed=True)
    record = core.build(order, ["S01"])
    assert core.qa_sample(order)["passed"]
    core.approve(order, "design", "synthetic test operator", confirmed=True)
    return record


def test_default_is_builtin_and_read_does_not_create_config(project):
    assert default_engine() == "builtin"
    assert not (project / ".pptstudio").exists()


def test_default_config_is_project_local_and_preserves_other_preferences(project, monkeypatch):
    core.write_json(project / ".pptstudio" / "config.json", {"schema_version": 1, "other": "keep"})
    result = configure_default("pptagent")
    assert result["default_engine"] == "pptagent"
    assert result["existing_orders_changed"] is False
    child = project / "nested"
    child.mkdir()
    monkeypatch.chdir(child)
    assert default_engine() == "pptagent"
    assert core.read_json(project / ".pptstudio" / "config.json")["other"] == "keep"


def test_default_affects_new_orders_not_existing_round(order):
    before = active_design(order)
    configure_default("pptagent")
    new = order.parent / "second"
    core.init_order(new, "新单", 1)
    initialized = initialize_design(new)
    assert initialized["engine"] == "pptagent"
    assert active_design(order) == before


def test_configure_requires_a_project_and_known_engine(tmp_path):
    with pytest.raises(core.WorkflowError, match="项目目录"):
        configure_default("builtin", tmp_path)
    with pytest.raises(core.WorkflowError, match="设计引擎"):
        configure_default("unknown", tmp_path)


def test_explicit_project_argument_does_not_fall_back_to_an_ancestor(project):
    child = project / "unrelated"
    child.mkdir()
    configure_default("pptagent", project)
    assert default_engine(child) == "builtin"
    with pytest.raises(core.WorkflowError, match="项目目录"):
        configure_default("builtin", child)
    assert default_engine(project) == "pptagent"


def test_malformed_default_is_not_silently_substituted(project):
    core.write_json(project / ".pptstudio" / "config.json", {"default_engine": "unknown"})
    with pytest.raises(core.WorkflowError, match="设计引擎"):
        default_engine()


def test_legacy_order_is_reported_without_migration(order):
    state = core.read_json(order / "state.json")
    state.pop("design")
    core.write_json(order / "state.json", state)
    before = (order / "state.json").read_bytes()
    assert active_design(order) == {"engine": "builtin", "attempt_id": "legacy", "label": "原有设计"}
    assert design_fingerprint(order) == {}
    assert (order / "state.json").read_bytes() == before


def test_initialize_is_idempotent_and_fingerprint_ignores_display_label(order):
    first = active_design(order)
    assert initialize_design(order, "builtin") == first
    before = design_fingerprint(order)
    state = core.read_json(order / "state.json")
    state["design"]["label"] = "仅改显示名称"
    core.write_json(order / "state.json", state)
    assert design_fingerprint(order) == before


def test_switch_preserves_plan_inputs_and_files_but_requires_new_design_confirmation(order):
    record = confirmed_sample(order)
    old = active_design(order)
    plan = core.read_json(order / "state.json")["approvals"]["plan"]
    original_deck = (order / "deck.json").read_bytes()
    original_style = (order / "style.json").read_bytes()
    result = switch_design(order, "pptagent", "第二种方式")
    state = core.read_json(order / "state.json")
    assert result["active"]["engine"] == "pptagent"
    assert result["active"]["attempt_id"] != old["attempt_id"]
    assert state["approvals"]["plan"] == plan
    assert core.approval_valid(order, "plan")
    assert "design" not in state["approvals"] and "final" not in state["approvals"]
    assert state["artifacts"] == {}
    assert (order / record["path"]).is_file()
    assert (order / "deck.json").read_bytes() == original_deck
    assert (order / "style.json").read_bytes() == original_style
    history = design_history(order)
    assert history["history"][-1]["artifacts"]["sample"] == record["path"]
    assert "deck" not in history["history"][-1]


def test_same_engine_still_starts_an_explicit_new_round(order):
    old = active_design(order)["attempt_id"]
    result = switch_design(order, "builtin", "重新设计")
    assert result["active"]["attempt_id"] != old
    assert result["archived"]["attempt_id"] == old


def test_invalid_engine_does_not_change_order(order):
    before = (order / "state.json").read_bytes()
    with pytest.raises(core.WorkflowError, match="设计引擎"):
        switch_design(order, "surprise")
    assert (order / "state.json").read_bytes() == before


def test_switch_blocks_an_existing_manual_baseline(order):
    state = core.read_json(order / "state.json")
    state["baseline"] = {"path": "build/manual.pptx"}
    core.write_json(order / "state.json", state)
    before = (order / "state.json").read_bytes()
    with pytest.raises(core.WorkflowError, match="人工基准"):
        switch_design(order, "pptagent")
    assert (order / "state.json").read_bytes() == before


def test_restore_returns_the_actual_previous_design_and_valid_confirmation(order):
    record = confirmed_sample(order)
    old = active_design(order)
    old_deck = core.read_json(order / "deck.json")
    old_style = core.read_json(order / "style.json")
    switch_design(order, "pptagent")
    style = core.read_json(order / "style.json")
    style["primary"] = "664422"
    core.write_json(order / "style.json", style)
    deck = core.read_json(order / "deck.json")
    deck["slides"][0]["body"] = ["其他方案的详细文案"]
    core.write_json(order / "deck.json", deck)
    result = restore_design(order, old["attempt_id"])
    assert result["active"] == old
    assert core.read_json(order / "deck.json") == old_deck
    assert core.read_json(order / "style.json") == old_style
    assert core.read_json(order / "state.json")["artifacts"]["sample"]["sha256"] == record["sha256"]
    assert core.approval_valid(order, "plan")
    assert core.approval_valid(order, "design")


def test_restore_retains_actual_full_file_and_prior_final_confirmation(order):
    confirmed_sample(order)
    full = core.build(order)
    assert core.qa(order)["passed"]
    core.approve(order, "final", "synthetic test operator", confirmed=True, visual_reviewed=True)
    old = active_design(order)["attempt_id"]
    prior = core.read_json(order / "state.json")["approvals"]["final"]
    switch_design(order, "pptagent")
    restore_design(order, old)
    restored = core.read_json(order / "state.json")
    assert restored["approvals"]["final"] == prior
    assert restored["artifacts"]["full"] == full
    assert (order / full["path"]).is_file()
    assert core.approval_valid(order, "final")


@pytest.mark.parametrize("change", ["facts", "outline", "requirements"])
def test_restore_rejects_changed_shared_facts_or_outline(order, change):
    old = active_design(order)["attempt_id"]
    switch_design(order, "pptagent")
    if change == "facts":
        core.write_json(order / "facts.json", {"facts": [{"id": "F001", "text": "新事实", "source_refs": []}]})
    elif change == "outline":
        deck = core.read_json(order / "deck.json")
        deck["slides"][0]["title"] = "新大纲标题"
        core.write_json(order / "deck.json", deck)
    else:
        brief = core.read_json(order / "brief.json")
        brief["requirements"] = "客户新增重点"
        core.write_json(order / "brief.json", brief)
    state_before = (order / "state.json").read_bytes()
    with pytest.raises(core.WorkflowError, match="大纲已变化"):
        restore_design(order, old)
    assert (order / "state.json").read_bytes() == state_before


def test_restore_rejects_uningested_source_changes(order):
    source = order / "sources" / "资料.md"
    source.write_text("old", encoding="utf-8")
    ingest_order(order)
    old = active_design(order)["attempt_id"]
    switch_design(order, "pptagent")
    source.write_text("new", encoding="utf-8")
    with pytest.raises(core.WorkflowError, match="ingest"):
        restore_design(order, old)


def test_restore_rejects_modified_snapshot(order):
    old = active_design(order)["attempt_id"]
    result = switch_design(order, "pptagent")
    snapshot = order / result["archived"]["snapshot_path"]
    snapshot.write_text("{}", encoding="utf-8")
    with pytest.raises(core.WorkflowError, match="快照缺失或已被修改"):
        restore_design(order, old)


def test_restore_rejects_snapshot_path_escape(order):
    old = active_design(order)["attempt_id"]
    switch_design(order, "pptagent")
    state = core.read_json(order / "state.json")
    state["design_history"][0]["snapshot_path"] = "../outside.json"
    core.write_json(order / "state.json", state)
    with pytest.raises(core.WorkflowError, match="目录内"):
        restore_design(order, old)


def test_restore_rejects_missing_or_changed_historical_pptx(order):
    record = confirmed_sample(order)
    old = active_design(order)["attempt_id"]
    switch_design(order, "pptagent")
    (order / record["path"]).write_bytes(b"changed")
    with pytest.raises(core.WorkflowError, match="历史设计文件"):
        restore_design(order, old)


def test_restore_confines_artifact_paths_even_with_matching_snapshot_hash(order):
    confirmed_sample(order)
    old = active_design(order)["attempt_id"]
    archived = switch_design(order, "pptagent")["archived"]
    snapshot = order / archived["snapshot_path"]
    payload = core.read_json(snapshot)
    payload["artifacts"]["sample"]["path"] = "../outside.pptx"
    core.write_json(snapshot, payload)
    state = core.read_json(order / "state.json")
    state["design_history"][0]["snapshot_sha256"] = core.file_hash(snapshot)
    core.write_json(order / "state.json", state)
    with pytest.raises(core.WorkflowError, match="目录内"):
        restore_design(order, old)


def test_legacy_restore_retains_legacy_digest_semantics(order):
    state = core.read_json(order / "state.json")
    state.pop("design")
    core.write_json(order / "state.json", state)
    confirmed_sample(order)
    switch_design(order, "pptagent")
    restore_design(order, "legacy")
    assert design_fingerprint(order) == {}
    assert core.approval_valid(order, "design")


def test_v01_payload_fingerprints_remain_valid_before_and_after_legacy_restore(order):
    """Freeze the 2f7c6fd algorithms instead of creating fixtures with new digests."""
    from PIL import Image
    from pptstudio.deck import build_deck

    def old_digest(value):
        serialized = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()

    def old_file_hash(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def load(name):
        return json.loads((order / name).read_text(encoding="utf-8-sig"))

    (order / "sources" / "legacy.md").write_text("客户确认的原始资料", encoding="utf-8")
    ingest_order(order)
    sources = load("sources.json")["files"]
    Image.new("RGB", (8, 8), "#226644").save(order / "assets" / "legacy.png")
    deck = load("deck.json")
    deck["slides"][0].update(image="assets/legacy.png", source_refs=[sources[0]["id"]])
    core.write_json(order / "deck.json", deck)
    core.write_json(order / "facts.json", {"facts": [
        {"id": "F001", "text": "客户确认的原始资料", "source_refs": [sources[0]["id"]]}
    ]})

    state = load("state.json")
    state.pop("design")
    # This is the unchanged renderer shipped by baseline commit 2f7c6fd.
    renderer = "67914e8d39c9f5d107d89b301bb47f52d6cf5a7fd133a8af9c8220160d1a0a1c"
    assert old_file_hash(Path(core.__file__).with_name("deck.py")) == renderer
    slides = deck["slides"]
    images = {s["image"]: old_file_hash(order / s["image"]) for s in slides if s.get("image")}
    old_model = old_digest({name: load(name) for name in ("brief.json", "deck.json", "style.json", "facts.json")} | {
        "sources": [{k: f.get(k) for k in ("id", "path", "sha256", "status", "text_sha256")} for f in sources],
        "images": images, "renderer": renderer,
    })
    old_plan = old_digest({"brief": load("brief.json"), "facts": load("facts.json"),
        "slides": [{k: s.get(k) for k in ("id", "title", "message", "source_refs")} for s in slides],
        "sources": [{k: f.get(k) for k in ("id", "sha256", "status", "text_sha256")} for f in sources],
    })

    # Produce real PPTX files directly; their old records intentionally have no
    # engine or attempt metadata and do not call current core.build/model_digest.
    for kind, selection in (("sample", ["S01"]), ("full", None)):
        path = order / "build" / f"legacy-{kind}.pptx"
        result = build_deck(order, path, slide_ids=selection)
        state["artifacts"][kind] = {"path": path.relative_to(order).as_posix(),
            "sha256": old_file_hash(path), "model_digest": old_model,
            "slide_ids": result["slide_ids"], "draft": False, "created_at": "2026-01-01T00:00:00+00:00"}
    sample = state["artifacts"]["sample"]
    chosen = set(sample["slide_ids"])
    old_design = old_digest({"style": load("style.json"), "sha256": sample["sha256"],
        "slides": [s for s in slides if s["id"] in chosen], "images": images, "renderer": renderer})
    sample["design_input"] = old_design
    full = state["artifacts"]["full"]
    old_final = old_digest({"sha256": full["sha256"], "model_digest": old_model,
                            "plan": old_plan, "design": old_design})
    state["approvals"] = {scope: {"by": "synthetic legacy customer fixture",
        "at": "2026-01-01T00:00:00+00:00", "note": "baseline compatibility test",
        "fingerprint": fingerprint, "visual_reviewed": scope == "final"}
        for scope, fingerprint in (("plan", old_plan), ("design", old_design), ("final", old_final))}
    core.write_json(order / "state.json", state)

    assert core.model_digest(order) == old_model
    assert core.design_digest(order) == old_design
    assert all(core.approval_valid(order, scope) for scope in ("plan", "design", "final"))
    assert core.current_artifact(order)[0] == full
    assert core.qa_sample(order)["passed"] and core.qa(order)["passed"]

    switch_design(order, "pptagent")
    assert core.approval_valid(order, "plan")
    assert not core.approval_valid(order, "design") and not core.approval_valid(order, "final")
    restored = restore_design(order, "legacy")
    assert restored["invalid_approvals_removed"] == []
    assert design_fingerprint(order) == {}
    assert core.model_digest(order) == old_model
    assert core.design_digest(order) == old_design
    assert core.read_json(order / "state.json")["artifacts"] == state["artifacts"]
    assert all(core.approval_valid(order, scope) for scope in ("plan", "design", "final"))


def test_restore_blocks_manual_baseline_and_invalid_attempt_ids(order):
    old = active_design(order)["attempt_id"]
    switch_design(order, "pptagent")
    with pytest.raises(core.WorkflowError, match="编号无效"):
        restore_design(order, "../../elsewhere")
    state = core.read_json(order / "state.json")
    state["baseline"] = {"path": "build/manual.pptx"}
    core.write_json(order / "state.json", state)
    with pytest.raises(core.WorkflowError, match="人工基准"):
        restore_design(order, old)


def test_repeat_archive_preserves_older_snapshots(order):
    first = active_design(order)["attempt_id"]
    saved = switch_design(order, "pptagent")["archived"]["snapshot_path"]
    restore_design(order, first)
    newer = switch_design(order, "builtin")["archived"]["snapshot_path"]
    assert saved != newer
    assert (order / saved).is_file() and (order / newer).is_file()


def test_invalid_saved_approval_is_not_reactivated(order):
    confirmed_sample(order)
    old = active_design(order)["attempt_id"]
    state = core.read_json(order / "state.json")
    state["approvals"]["design"]["fingerprint"] = "invalid"
    core.write_json(order / "state.json", state)
    switch_design(order, "pptagent")
    result = restore_design(order, old)
    assert result["invalid_approvals_removed"] == ["design"]
    assert "design" not in core.read_json(order / "state.json")["approvals"]
