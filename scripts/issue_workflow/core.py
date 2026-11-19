"""Pure logic for the issue-driven workflow: parsing, body building and the gate.

No external calls, no file I/O, no mutation of inputs. ``github``/``cli`` are
deliberately not imported - this module is fully testable in isolation.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from . import markers, templates
from .templates import DEFAULT_ACCEPTANCE, DEFAULT_PROCESS  # re-exported for cli

__all__ = [
    "DEFAULT_ACCEPTANCE",
    "DEFAULT_PROCESS",
    "ChecklistItem",
    "GateResult",
    "IssueMarkers",
    "MarkerError",
    "TaskSpec",
    "build_main_body",
    "build_sub_body",
    "evaluate_gate",
    "format_report",
    "is_checklist_complete",
    "mark_checklist",
    "parse_checklist",
    "parse_markers",
    "parse_task_specs",
    "validate_sub_body",
]


class MarkerError(ValueError):
    """Raised when a required marker is missing or malformed."""


@dataclass(frozen=True)
class IssueMarkers:
    role: str
    change_id: str
    task_id: str | None


@dataclass(frozen=True)
class ChecklistItem:
    text: str
    checked: bool


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    title: str


@dataclass(frozen=True)
class GateResult:
    ok: bool
    reasons: tuple[str, ...]
    checks: dict[str, bool]
    checks_complete: bool = True


_ID = r"[A-Za-z0-9._-]+"
_MARKER_RE = re.compile(
    r"<!--\s*"
    + re.escape(markers.METADATA_MARKER)
    + r"\s+"
    + rf"role=(?P<role>{_ID})"
    + r"\s+"
    + rf"change=(?P<change>{_ID})"
    + rf"(?:\s+task=(?P<task>{_ID}))?"
    + r"\s*-->"
)
_CHECK_RE = re.compile(r"^-\s*\[(?P<box>[ xX])\]\s*(?P<text>.*)$")
_TASK_RE = re.compile(
    r"^\s*-\s*\[[ xX]\]\s+(?P<id>\d+(?:\.\d+)*)\.?(?:\s+|$)(?P<title>.*)$"
)


def parse_markers(body: str) -> IssueMarkers:
    if not isinstance(body, str):
        raise MarkerError("body must be a string")
    match = _MARKER_RE.search(body)
    if match is None:
        raise MarkerError("missing or malformed issue-workflow marker")
    role = match.group("role")
    if role not in ("main", "sub"):
        raise MarkerError(f"invalid role: {role}")
    change_id = match.group("change")
    if not change_id:
        raise MarkerError("empty change id")
    return IssueMarkers(role=role, change_id=change_id, task_id=match.group("task"))


def parse_checklist(
    body: str, start: str, end: str
) -> tuple[ChecklistItem, ...]:
    if not isinstance(body, str):
        raise MarkerError("body must be a string")
    begin = body.find(start)
    finish = body.find(end)
    if begin == -1 or finish == -1 or finish <= begin:
        raise MarkerError("missing or misordered checklist markers")
    section = body[begin + len(start) : finish]
    items = []
    for raw_line in section.splitlines():
        match = _CHECK_RE.match(raw_line.strip())
        if match is not None:
            items.append(
                ChecklistItem(
                    text=match.group("text").strip(),
                    checked=match.group("box").lower() == "x",
                )
            )
    return tuple(items)


def parse_task_specs(tasks_md: str) -> tuple[TaskSpec, ...]:
    if not isinstance(tasks_md, str):
        raise MarkerError("tasks_md must be a string")
    specs = []
    for raw_line in tasks_md.splitlines():
        match = _TASK_RE.match(raw_line)
        if match is None:
            continue
        title = match.group("title").strip()
        if title:
            specs.append(TaskSpec(task_id=match.group("id"), title=title))
    return tuple(specs)


def _render_marker(role: str, change_id: str, task_id: str | None = None) -> str:
    attrs = f"{markers.METADATA_MARKER} role={role} change={change_id}"
    if task_id is not None:
        attrs += f" task={task_id}"
    return f"<!-- {attrs} -->"


def _check_line(text: str) -> str:
    return f"- [ ] {text}"


def _sub_line(sub: dict) -> str:
    box = "x" if sub.get("state") == "CLOSED" else " "
    return f"- [{box}] #{sub.get('number', '?')} — {sub.get('title', '')}"


def build_main_body(
    change_id: str,
    criteria: Sequence[str],
    repo: str,
    summary: str = "",
    sub_issues: Sequence[dict] = (),
    criteria_checked: bool = False,
) -> str:
    parts = [
        _render_marker("main", change_id),
        f"# OpenSpec change: {change_id}",
        templates.BRANCH_TEMPLATE.format(change_id=change_id),
        templates.REPO_TEMPLATE.format(repo=repo),
    ]
    if summary:
        parts.append(templates.SUMMARY_TEMPLATE.format(summary=summary))
    parts.extend(
        [
            "",
            templates.SECTION_CRITERIA,
            markers.CRITERIA_START,
            *(
                f"- [{'x' if criteria_checked else ' '}] {item}"
                for item in criteria
            ),
            markers.CRITERIA_END,
            "",
            templates.SECTION_SUB_ISSUES,
            *(_sub_line(sub) for sub in sub_issues),
        ]
    )
    return "\n".join(parts)


def build_sub_body(
    change_id: str,
    task: TaskSpec,
    main_number: int,
    role: str,
    scope: str,
    process: Sequence[str],
    merge_gate: str,
    handoff: str = "",
    acceptance: Sequence[str] = (),
) -> str:
    steps = tuple(process) if process else DEFAULT_PROCESS
    criteria = tuple(acceptance) if acceptance else steps
    parts = [
        _render_marker("sub", change_id, task.task_id),
        f"# Sub-issue {task.task_id}: {task.title}",
        templates.PART_OF_TEMPLATE.format(number=main_number),
        "",
        templates.SECTION_ROLE,
        templates.ROLE_TEMPLATE.format(role=role, change_id=change_id),
        "",
        templates.SECTION_SCOPE,
        scope,
        "",
        templates.SECTION_PROCESS,
        *(f"{index}. {step}" for index, step in enumerate(steps, start=1)),
        "",
        templates.SECTION_ACCEPTANCE,
        markers.ACCEPTANCE_START,
        *(_check_line(item) for item in criteria),
        markers.ACCEPTANCE_END,
        "",
        templates.SECTION_MERGE_GATE,
        merge_gate,
        "",
        templates.SECTION_EVIDENCE,
        templates.EVIDENCE_PLACEHOLDER,
        "",
        templates.SECTION_HANDOFF,
        handoff or templates.HANDOFF_PLACEHOLDER,
    ]
    return "\n".join(parts)


def _checklist_state(body: str, start: str, end: str) -> bool:
    try:
        items = parse_checklist(body, start, end)
    except MarkerError:
        return False
    return bool(items) and all(item.checked for item in items)


def is_checklist_complete(body: str, start: str, end: str) -> bool:
    """Публичная проверка: все пункты между маркерами отмечены."""
    return _checklist_state(body, start, end)


def mark_checklist(body: str, start: str, end: str) -> str:
    """Отметить пункты только между маркерами, не меняя остальной текст."""
    begin = body.find(start)
    finish = body.find(end)
    if begin == -1 or finish == -1 or finish <= begin:
        raise MarkerError("missing or misordered checklist markers")
    section_start = begin + len(start)
    updated = body[section_start:finish].replace("- [ ]", "- [x]")
    return body[:section_start] + updated + body[finish:]


def _sub_reasons(sub_issues: Sequence[dict]) -> list[str]:
    reasons = []
    for sub in sub_issues:
        number = sub.get("number", "?")
        state = sub.get("state")
        if state != "CLOSED":
            reasons.append(f"issue #{number}: state={state!r}, ожидалось CLOSED")
        if not _checklist_state(
            sub.get("body", ""), markers.ACCEPTANCE_START, markers.ACCEPTANCE_END
        ):
            reasons.append(
                f"issue #{number}: критерии приёмки отсутствуют или не отмечены"
            )
    return reasons


def _check_reasons(checks: dict[str, bool]) -> list[str]:
    return [
        f"проверка '{name}' не пройдена"
        for name, value in checks.items()
        if value is not True
    ]


def _marker_reasons(
    body: str, expected_change: str, role: str, number: object = ""
) -> list[str]:
    prefix = f"issue #{number}: " if number != "" else "главный issue: "
    try:
        meta = parse_markers(body)
    except MarkerError as exc:
        return [f"{prefix}маркер отсутствует или повреждён ({exc})"]
    reasons = []
    if meta.role != role:
        reasons.append(f"{prefix}роль {meta.role!r}, ожидалось {role!r}")
    if not meta.change_id:
        reasons.append(f"{prefix}пустой change id")
    elif expected_change and meta.change_id != expected_change:
        reasons.append(f"{prefix}change {meta.change_id!r}, ожидалось {expected_change!r}")
    return reasons


def validate_sub_body(body: str) -> tuple[str, ...]:
    """Проверить тело sub-issue до создания: секции, маркер, критерии приёмки."""
    reasons: list[str] = []
    try:
        meta = parse_markers(body)
    except MarkerError as exc:
        reasons.append(str(exc))
    else:
        if meta.role != "sub":
            reasons.append(f"роль {meta.role!r}, ожидалось 'sub'")
        if not meta.task_id:
            reasons.append("отсутствует task id в маркере")
    required = (
        templates.SECTION_ROLE,
        templates.SECTION_SCOPE,
        templates.SECTION_PROCESS,
        templates.SECTION_ACCEPTANCE,
        templates.SECTION_MERGE_GATE,
        templates.SECTION_EVIDENCE,
        templates.SECTION_HANDOFF,
    )
    missing = [title for title in required if title not in body]
    if missing:
        reasons.append(f"отсутствуют секции: {', '.join(missing)}")
    try:
        items = parse_checklist(body, markers.ACCEPTANCE_START, markers.ACCEPTANCE_END)
    except MarkerError as exc:
        reasons.append(str(exc))
    else:
        if not items:
            reasons.append("чеклист критериев приёмки пуст")
    return tuple(reasons)


def evaluate_gate(
    *,
    sub_issues: Sequence[dict],
    expected_count: int,
    main_body: str,
    checks: dict[str, bool],
    expected_change_id: str = "",
    expected_task_ids: Sequence[str] = (),
    checks_complete: bool = True,
    main_state: str = "",
) -> GateResult:
    reasons: list[str] = []
    if expected_count <= 0:
        reasons.append(f"expected_count должно быть > 0 (получено {expected_count})")
    if len(sub_issues) != expected_count:
        reasons.append(
            f"число sub-issues {len(sub_issues)} != ожидаемому {expected_count}"
        )
    reasons.extend(_sub_reasons(sub_issues))
    if not _checklist_state(
        main_body, markers.CRITERIA_START, markers.CRITERIA_END
    ):
        reasons.append("главный issue: чеклист критериев отсутствует или не отмечен")
    reasons.extend(_check_reasons(checks))
    if main_state == "CLOSED":
        reasons.append("главный issue уже закрыт")
    reasons.extend(_marker_reasons(main_body, expected_change_id, "main"))
    actual_tasks: Counter[str] = Counter()
    for sub in sub_issues:
        body = sub.get("body", "")
        reasons.extend(
            _marker_reasons(body, expected_change_id, "sub", sub.get("number", "?"))
        )
        try:
            meta = parse_markers(body)
        except MarkerError:
            continue
        if meta.task_id:
            actual_tasks[meta.task_id] += 1
    if expected_task_ids and actual_tasks != Counter(expected_task_ids):
        reasons.append(
            f"идентификаторы задач {sorted(actual_tasks.elements())} != "
            f"ожидаемым {sorted(expected_task_ids)}"
        )
    ok = (
        not reasons
        and checks_complete
        and all(value is True for value in checks.values())
    )
    return GateResult(
        ok=ok,
        reasons=tuple(reasons),
        checks=dict(checks),
        checks_complete=checks_complete,
    )


def format_report(result: GateResult) -> str:
    if result.ok:
        title = "GATE PASSED"
    elif not result.checks_complete:
        title = "GATE INCOMPLETE — проверки пропущены"
    else:
        title = "GATE FAILED"
    lines = [title]
    lines.extend(f"  - {reason}" for reason in result.reasons)
    lines.append("Checks:")
    for name, passed in result.checks.items():
        lines.append(f"  - {name}: {'PASS' if passed is True else 'FAIL'}")
    return "\n".join(lines)
