"""Optional design engines and reversible, evidence-preserving design rounds.

The module manages local preferences and order state only. Selecting PPTAgent
never installs a runtime, calls a model, or substitutes another engine.
"""
from __future__ import annotations

import copy
import re
import uuid
from pathlib import Path

ENGINES = frozenset({"builtin", "pptagent"})
_ATTEMPT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")


def _engine(value: str) -> str:
    from .core import WorkflowError
    if not isinstance(value, str) or value not in ENGINES:
        raise WorkflowError("设计引擎须为 builtin 或 pptagent。")
    return value


def _project_root(project: Path | None = None) -> Path | None:
    """Resolve an explicit root exactly; discover ancestors only from cwd."""
    start = Path(project) if project is not None else Path.cwd()
    start = start.resolve()
    if start.is_file():
        start = start.parent
    candidates = (start,) if project is not None else (start, *start.parents)
    for candidate in candidates:
        marker = candidate / "pyproject.toml"
        if marker.is_file():
            text = marker.read_text(encoding="utf-8-sig")
            if re.search(r'(?m)^name\s*=\s*[\"\']ppt-order-studio[\"\']\s*$', text):
                return candidate
    return None


def _safe(root: Path, relative: str) -> Path:
    from .core import WorkflowError
    rel = Path(relative)
    if rel.is_absolute() or ".." in relative.replace("\\", "/").split("/"):
        raise WorkflowError("设计记录路径必须位于项目或订单目录内。")
    root = root.resolve()
    path = root / rel
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise WorkflowError("设计记录不支持符号链接。")
    path = path.resolve()
    if not path.is_relative_to(root):
        raise WorkflowError("设计记录路径越界。")
    return path


def default_engine(project: Path | None = None) -> str:
    """Read a project-local default; no project/config means builtin."""
    from .core import WorkflowError, read_json
    root = _project_root(project)
    if root is None:
        return "builtin"
    path = _safe(root, ".pptstudio/config.json")
    if not path.exists():
        return "builtin"
    config = read_json(path)
    if not isinstance(config, dict) or config.get("schema_version", 1) != 1:
        raise WorkflowError(".pptstudio/config.json 格式或版本无效。")
    return _engine(config.get("default_engine", "builtin"))


def configure_default(engine: str, project: Path | None = None) -> dict:
    from .core import WorkflowError, read_json, write_json
    engine = _engine(engine)
    root = _project_root(project)
    if root is None:
        raise WorkflowError("请在 PPT Order Studio 项目目录中配置默认设计引擎。")
    path = _safe(root, ".pptstudio/config.json")
    config = read_json(path, {})
    if not isinstance(config, dict) or config.get("schema_version", 1) != 1:
        raise WorkflowError("已有项目配置格式或版本无效。")
    config.update(schema_version=1, default_engine=engine)
    write_json(path, config)
    return {"project": str(root), "config_path": str(path), "default_engine": engine,
            "existing_orders_changed": False}


def _validated_design(value: dict) -> dict:
    from .core import WorkflowError
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise WorkflowError("订单设计配置格式或版本无效。")
    _engine(value.get("engine"))
    attempt = value.get("attempt_id")
    if not isinstance(attempt, str) or not _ATTEMPT_ID.fullmatch(attempt):
        raise WorkflowError("设计轮次编号无效。")
    return copy.deepcopy(value)


def active_design(order: Path) -> dict:
    """Report v0.1 orders without upgrading or changing their fingerprints."""
    from .core import read_json, require_order
    order = require_order(Path(order))
    state = read_json(order / "state.json")
    if "design" not in state:
        return {"engine": "builtin", "attempt_id": "legacy", "label": "原有设计"}
    return _validated_design(state["design"])


def _new_design(engine: str, label: str = "") -> dict:
    from .core import now
    return {"schema_version": 1, "engine": _engine(engine),
            "attempt_id": "design-" + uuid.uuid4().hex[:12],
            "label": label.strip() or ("内置设计" if engine == "builtin" else "PPTAgent 设计"),
            "created_at": now()}


def initialize_design(order: Path, engine: str | None = None) -> dict:
    from .core import read_json, require_order, write_json
    order = require_order(Path(order))
    state = read_json(order / "state.json")
    if "design" in state:
        return active_design(order)
    design = _new_design(default_engine() if engine is None else engine)
    _safe(order, "designs/" + design["attempt_id"]).mkdir(parents=True, exist_ok=False)
    state["design"] = design
    write_json(order / "state.json", state)
    return copy.deepcopy(design)


def design_fingerprint(order: Path) -> dict:
    from .core import read_json, require_order
    order = require_order(Path(order))
    state = read_json(order / "state.json")
    if "design" not in state:
        return {}
    design = _validated_design(state["design"])
    return {key: design[key] for key in ("schema_version", "engine", "attempt_id")}


def _no_manual_baseline(state: dict):
    from .core import WorkflowError
    if state.get("baseline"):
        raise WorkflowError("已有人工基准，不能切换或恢复设计轮次。请继续基于该稿修改；大规模重做另建订单并保留原稿。")


def _archive(order: Path, state: dict) -> dict:
    """Write a new snapshot without changing live state or invoking artifacts."""
    from .core import file_hash, now, plan_digest, read_json, write_json
    design = active_design(order)
    relative = "designs/" + design["attempt_id"] + "/snapshot-" + uuid.uuid4().hex[:12] + ".json"
    path = _safe(order, relative)
    payload = {"schema_version": 1, "design": copy.deepcopy(state.get("design")),
               "plan_fingerprint": plan_digest(order), "deck": read_json(order / "deck.json"),
               "style": read_json(order / "style.json"), "artifacts": copy.deepcopy(state.get("artifacts", {})),
               "baseline": copy.deepcopy(state.get("baseline")),
               "approvals": {scope: copy.deepcopy(state.get("approvals", {})[scope])
                             for scope in ("design", "final") if scope in state.get("approvals", {})},
               "archived_at": now()}
    write_json(path, payload)
    metadata = {"attempt_id": design["attempt_id"], "engine": design["engine"],
                "label": design.get("label", ""), "snapshot_path": relative,
                "snapshot_sha256": file_hash(path), "archived_at": payload["archived_at"],
                "plan_fingerprint": payload["plan_fingerprint"],
                "artifacts": {name: record.get("path") for name, record in payload["artifacts"].items()
                              if isinstance(record, dict) and record.get("path")}}
    history = [item for item in state.get("design_history", [])
               if item.get("attempt_id") != design["attempt_id"]]
    state["design_history"] = [*history, metadata]
    return metadata


def switch_design(order: Path, engine: str, label: str = "") -> dict:
    from .core import read_json, require_order, write_json
    engine = _engine(engine)
    order = require_order(Path(order))
    state = read_json(order / "state.json")
    _no_manual_baseline(state)
    archived = _archive(order, state)
    design = _new_design(engine, label)
    _safe(order, "designs/" + design["attempt_id"]).mkdir(parents=True, exist_ok=False)
    state["design"] = design
    state["artifacts"] = {}
    state["baseline"] = None
    for scope in ("design", "final"):
        state.setdefault("approvals", {}).pop(scope, None)
    write_json(order / "state.json", state)
    return {"active": copy.deepcopy(design), "archived": archived,
            "note": "上一轮文件已保留。内容未变化时大纲确认继续有效；新样张与最终验收需重新确认。"}


def _snapshot(order: Path, metadata: dict) -> dict:
    from .core import WorkflowError, file_hash, read_json
    path = _safe(order, metadata["snapshot_path"])
    if not path.is_file() or file_hash(path) != metadata.get("snapshot_sha256"):
        raise WorkflowError("设计快照缺失或已被修改，不能恢复。")
    payload = read_json(path)
    if payload.get("schema_version") != 1:
        raise WorkflowError("设计快照版本无效。")
    saved_design = payload.get("design")
    if saved_design is not None:
        value = _validated_design(saved_design)
        if value["attempt_id"] != metadata.get("attempt_id") or value["engine"] != metadata.get("engine"):
            raise WorkflowError("设计快照与轮次记录不一致。")
    elif metadata.get("attempt_id") != "legacy" or metadata.get("engine") != "builtin":
        raise WorkflowError("旧版设计快照记录不一致。")
    for name in ("deck", "style", "artifacts", "approvals"):
        if not isinstance(payload.get(name), dict):
            raise WorkflowError("设计快照内容格式无效。")
    return payload


def restore_design(order: Path, attempt_id: str) -> dict:
    from .core import (WorkflowError, approval_valid, assert_sources_current, file_hash,
                       plan_digest, read_json, require_order, write_json)
    order = require_order(Path(order))
    state = read_json(order / "state.json")
    _no_manual_baseline(state)
    if not isinstance(attempt_id, str) or not _ATTEMPT_ID.fullmatch(attempt_id):
        raise WorkflowError("设计轮次编号无效。")
    if active_design(order)["attempt_id"] == attempt_id:
        raise WorkflowError("该轮次已经是当前设计。")
    matches = [row for row in state.get("design_history", []) if row.get("attempt_id") == attempt_id]
    if not matches:
        raise WorkflowError("未找到该历史设计轮次。")
    payload = _snapshot(order, matches[-1])
    assert_sources_current(order)
    if payload.get("plan_fingerprint") != plan_digest(order):
        raise WorkflowError("资料、事实、需求或大纲已变化，不能直接恢复旧设计。请在当前内容上开始新轮次。")
    for record in payload["artifacts"].values():
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise WorkflowError("设计快照中的文件记录无效。")
        path = _safe(order, record["path"])
        if not path.is_file() or file_hash(path) != record.get("sha256"):
            raise WorkflowError("历史设计文件缺失或已变化，不能恢复。")
    original = {name: (order / name).read_bytes() for name in ("deck.json", "style.json", "state.json")}
    archived = _archive(order, state)
    if payload["design"] is None:
        state.pop("design", None)
    else:
        state["design"] = copy.deepcopy(payload["design"])
    state["artifacts"] = copy.deepcopy(payload["artifacts"])
    state["baseline"] = copy.deepcopy(payload.get("baseline"))
    for scope in ("design", "final"):
        state.setdefault("approvals", {}).pop(scope, None)
        if scope in payload["approvals"]:
            state["approvals"][scope] = copy.deepcopy(payload["approvals"][scope])
    dropped = []
    try:
        write_json(order / "deck.json", payload["deck"])
        write_json(order / "style.json", payload["style"])
        write_json(order / "state.json", state)
        for scope in ("design", "final"):
            if scope in state["approvals"] and not approval_valid(order, scope):
                state["approvals"].pop(scope)
                dropped.append(scope)
        if dropped:
            write_json(order / "state.json", state)
    except Exception:
        for name, value in original.items():
            (order / name).write_bytes(value)
        raise
    return {"active": active_design(order), "archived": archived, "restored": attempt_id,
            "invalid_approvals_removed": dropped,
            "note": "已切回该轮页面、样式及实际文件；仅保留当前指纹仍有效的历史确认。"}


def design_history(order: Path) -> dict:
    from .core import read_json, require_order
    order = require_order(Path(order))
    state = read_json(order / "state.json")
    return {"active": active_design(order), "history": copy.deepcopy(state.get("design_history", [])),
            "manual_baseline": bool(state.get("baseline")),
            "active_artifacts": {name: row.get("path") for name, row in state.get("artifacts", {}).items()
                                 if isinstance(row, dict) and row.get("path")}}
