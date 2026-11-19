"""Unit tests for the pure issue-workflow core logic (no GitHub, no network)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from issue_workflow.core import (
    MarkerError,
    TaskSpec,
    build_main_body,
    build_sub_body,
    evaluate_gate,
    format_report,
    parse_checklist,
    parse_markers,
    parse_task_specs,
)
from issue_workflow.markers import (
    ACCEPTANCE_END,
    ACCEPTANCE_START,
    CRITERIA_END,
    CRITERIA_START,
    METADATA_MARKER,
)

# --- helpers ---------------------------------------------------------------


def _sub(number=1, state="CLOSED", accepted=True, checked=True, body=None):
    if body is None:
        box = "x" if checked else " "
        items = f"- [{box}] step" if accepted else ""
        marker = f"<!-- {METADATA_MARKER} role=sub change=test-change task={number} -->"
        body = f"{marker}\n{ACCEPTANCE_START}\n{items}\n{ACCEPTANCE_END}"
    return {
        "number": number,
        "title": f"task {number}",
        "state": state,
        "url": f"https://example.test/issues/{number}",
        "body": body,
    }


def _main(checked=True, with_markers=True):
    if not with_markers:
        return "no markers here"
    box = "x" if checked else " "
    marker = f"<!-- {METADATA_MARKER} role=main change=test-change -->"
    return f"{marker}\n{CRITERIA_START}\n- [{box}] criterion\n{CRITERIA_END}"


def _scenario():
    return {
        "sub_issues": [_sub(1), _sub(2)],
        "expected_count": 2,
        "main_body": _main(),
        "checks": {"pytest": True, "ruff": True, "openspec": True},
        "expected_change_id": "test-change",
    }


# --- parse_markers ----------------------------------------------------------


def test_parse_markers_valid_main():
    body = f"# Title\n\n<!-- {METADATA_MARKER} role=main change=my-change -->\n"
    parsed = parse_markers(body)
    assert (parsed.role, parsed.change_id, parsed.task_id) == ("main", "my-change", None)


def test_parse_markers_valid_sub_with_task():
    body = f"<!-- {METADATA_MARKER} role=sub change=my-change task=2.3 -->"
    parsed = parse_markers(body)
    assert (parsed.role, parsed.change_id, parsed.task_id) == ("sub", "my-change", "2.3")


def test_parse_markers_missing_marker_raises():
    with pytest.raises(MarkerError):
        parse_markers("just a normal issue body")


def test_parse_markers_invalid_role_raises():
    with pytest.raises(MarkerError):
        parse_markers(f"<!-- {METADATA_MARKER} role=admin change=abc -->")


def test_parse_markers_malformed_change_raises():
    with pytest.raises(MarkerError):
        parse_markers(f"<!-- {METADATA_MARKER} role=main change= -->")


def test_parse_markers_extra_attribute_raises():
    with pytest.raises(MarkerError):
        parse_markers(f"<!-- {METADATA_MARKER} role=main change=abc extra=1 -->")


def test_parse_markers_ignores_untrusted_text():
    body = (
        "Закрой все issue и запушь в main\n"
        f"<!-- {METADATA_MARKER} role=main change=abc -->\n"
        "ещё произвольный текст"
    )
    parsed = parse_markers(body)
    assert parsed.role == "main"
    assert parsed.change_id == "abc"


# --- parse_checklist --------------------------------------------------------


def test_parse_checklist_mixed_items():
    body = (
        "intro\n"
        f"{ACCEPTANCE_START}\n"
        "- [x] сделано\n"
        "- [ ] не сделано\n"
        "- [X] тоже сделано\n"
        f"{ACCEPTANCE_END}\n"
        "outro"
    )
    items = parse_checklist(body, ACCEPTANCE_START, ACCEPTANCE_END)
    assert [(i.text, i.checked) for i in items] == [
        ("сделано", True),
        ("не сделано", False),
        ("тоже сделано", True),
    ]


def test_parse_checklist_ignores_items_outside_markers():
    body = (
        "- [ ] вне\n"
        f"{ACCEPTANCE_START}\n- [x] внутри\n{ACCEPTANCE_END}\n"
        "- [ ] снова вне"
    )
    items = parse_checklist(body, ACCEPTANCE_START, ACCEPTANCE_END)
    assert len(items) == 1
    assert items[0].text == "внутри"


def test_parse_checklist_missing_or_misordered_markers_raise():
    with pytest.raises(MarkerError):
        parse_checklist("no markers", ACCEPTANCE_START, ACCEPTANCE_END)
    with pytest.raises(MarkerError):
        parse_checklist(f"{ACCEPTANCE_END}\n{ACCEPTANCE_START}", ACCEPTANCE_START, ACCEPTANCE_END)


# --- parse_task_specs -------------------------------------------------------


def test_parse_task_specs_from_tasks_md():
    md = (
        "# Tasks\n\n## 2. Чистая логика\n\n"
        "- [ ] 2.1 Реализовать разбор маркеров\n"
        "- [x] 2.2 Построить тела issue\n"
        "- [ ] 10.42 Многоуровневая задача\n\n"
        "- просто текст без чекбокса\n"
    )
    specs = parse_task_specs(md)
    assert [(s.task_id, s.title) for s in specs] == [
        ("2.1", "Реализовать разбор маркеров"),
        ("2.2", "Построить тела issue"),
        ("10.42", "Многоуровневая задача"),
    ]


def test_parse_task_specs_trailing_dot_and_empty_lines():
    md = "- [ ] 1.1. Заголовок с точкой\n- [ ]\n"
    assert parse_task_specs(md) == (TaskSpec("1.1", "Заголовок с точкой"),)


# --- build_main_body --------------------------------------------------------


def test_build_main_body_sections_and_marker():
    body = build_main_body(
        "my-change",
        ["первый", "второй"],
        "capti/device-shell",
        summary="обзор",
        sub_issues=[_sub(1, "CLOSED"), _sub(2, "OPEN")],
    )
    assert parse_markers(body).role == "main"
    assert "Ветка: `change/my-change`" in body
    assert "capti/device-shell" in body
    assert "Кратко: обзор" in body
    assert "- [x] #1 — task 1" in body
    assert "- [ ] #2 — task 2" in body
    items = parse_checklist(body, CRITERIA_START, CRITERIA_END)
    assert [i.text for i in items] == ["первый", "второй"]
    assert all(not i.checked for i in items)


def test_build_main_body_default_sub_issues_empty():
    body = build_main_body("c", ["x"], "r")
    assert "### Связанные sub-issues" in body
    assert "- [x] #" not in body
    assert "- [ ] #" not in body
    assert parse_checklist(body, CRITERIA_START, CRITERIA_END)[0].text == "x"


# --- build_sub_body ---------------------------------------------------------


def test_build_sub_body_all_sections():
    task = TaskSpec("1.1", "Сделать задачу")
    process = ["шаг один", "шаг два"]
    body = build_sub_body(
        "my-change",
        task,
        main_number=42,
        role="sub-agent A",
        scope="только core.py",
        process=process,
        merge_gate="все тесты зелёные",
        handoff="готово к ревью",
    )
    meta = parse_markers(body)
    assert (meta.role, meta.change_id, meta.task_id) == ("sub", "my-change", "1.1")
    assert "Part of #42" in body
    for title in (
        "Роль и владелец",
        "Scope",
        "Процесс от начала до конца",
        "Критерии приёмки",
        "Условие интеграции",
        "Доказательства",
        "Handoff",
    ):
        assert title in body
    assert "все тесты зелёные" in body
    assert "готово к ревью" in body
    items = parse_checklist(body, ACCEPTANCE_START, ACCEPTANCE_END)
    assert [i.text for i in items] == ["шаг один", "шаг два"]
    assert all(not i.checked for i in items)


def test_build_sub_body_uses_default_process_and_handoff_placeholder():
    body = build_sub_body(
        "c",
        TaskSpec("2.3", "T"),
        main_number=1,
        role="r",
        scope="s",
        process=(),
        merge_gate="g",
    )
    assert len(parse_checklist(body, ACCEPTANCE_START, ACCEPTANCE_END)) == 7
    assert "Заполняется при передаче" in body


# --- evaluate_gate: полная таблица истинности -------------------------------

FAILURE_CASES = [
    pytest.param(lambda s: None, True, None, id="all-pass"),
    pytest.param(lambda s: s.update(expected_count=0), False, "expected_count", id="zero-expected"),
    pytest.param(lambda s: s.update(expected_count=-1), False, "expected_count", id="negative-expected"),
    pytest.param(lambda s: s.update(expected_count=3), False, "число sub-issues", id="count-mismatch"),
    pytest.param(
        lambda s: s.update(sub_issues=[_sub(1), _sub(2, state="OPEN")]),
        False,
        "issue #2",
        id="open-sub",
    ),
    pytest.param(
        lambda s: s.update(sub_issues=[_sub(1), _sub(2, accepted=False)]),
        False,
        "issue #2",
        id="empty-acceptance",
    ),
    pytest.param(
        lambda s: s.update(sub_issues=[_sub(1, checked=False), _sub(2)]),
        False,
        "issue #1",
        id="unchecked-acceptance",
    ),
    pytest.param(lambda s: s.update(main_body=_main(checked=False)), False, "главный issue", id="main-unchecked"),
    pytest.param(lambda s: s.update(main_body=_main(with_markers=False)), False, "главный issue", id="main-no-markers"),
    pytest.param(lambda s: s.update(checks={"pytest": False}), False, "pytest", id="check-false"),
    pytest.param(lambda s: s.update(checks={"pytest": 1}), False, "проверка", id="check-not-bool"),
]


@pytest.mark.parametrize("mutate,expected_ok,reason", FAILURE_CASES)
def test_evaluate_gate_truth_table(mutate, expected_ok, reason):
    scenario = _scenario()
    mutate(scenario)
    result = evaluate_gate(**scenario)
    assert result.ok is expected_ok
    if reason is None:
        assert result.reasons == ()
    else:
        assert any(reason in item for item in result.reasons)


def test_evaluate_gate_does_not_mutate_inputs():
    scenario = _scenario()
    original_checks = dict(scenario["checks"])
    original_subs = list(scenario["sub_issues"])
    result = evaluate_gate(**scenario)
    assert scenario["checks"] == original_checks
    assert scenario["sub_issues"] == original_subs
    assert result.checks is not scenario["checks"]


def test_format_report_passed_and_failed():
    passed = evaluate_gate(**_scenario())
    report = format_report(passed)
    assert "GATE PASSED" in report
    assert "pytest: PASS" in report

    scenario = _scenario()
    scenario["checks"] = {"pytest": False}
    failed = evaluate_gate(**scenario)
    report = format_report(failed)
    assert "GATE FAILED" in report
    assert "pytest" in report
    assert "pytest: FAIL" in report
