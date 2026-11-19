"""Проверки гейта после ужесточения: маркеры и критерии приёмки."""

from issue_workflow import core
from issue_workflow.markers import ACCEPTANCE_END, ACCEPTANCE_START


def _checked(body: str) -> str:
    return body.replace("- [ ]", "- [x]")


def _sub_body(change_id: str = "change-x") -> str:
    return core.build_sub_body(
        change_id,
        core.TaskSpec("1.1", "Задача"),
        main_number=1,
        role="subagent",
        scope="scope",
        process=("шаг процесса",),
        merge_gate="green",
        acceptance=("результат задачи",),
    )


def test_explicit_acceptance_replaces_process_steps():
    body = core.build_sub_body(
        "change-x",
        core.TaskSpec("1.1", "Задача"),
        main_number=1,
        role="subagent",
        scope="scope",
        process=("шаг процесса",),
        merge_gate="green",
        acceptance=("результат A", "результат B"),
    )
    items = core.parse_checklist(body, ACCEPTANCE_START, ACCEPTANCE_END)
    assert [item.text for item in items] == ["результат A", "результат B"]
    assert "шаг процесса" not in [item.text for item in items]


def _gate(sub_body: str, main_body: str, change_id: str = "change-x"):
    sub = {
        "number": 2,
        "title": "Задача",
        "state": "CLOSED",
        "url": "https://example.test/issues/2",
        "body": _checked(sub_body),
    }
    return core.evaluate_gate(
        sub_issues=[sub],
        expected_count=1,
        main_body=_checked(main_body),
        checks={"pytest": True},
        expected_change_id=change_id,
        expected_task_ids=("1.1",),
    )


def test_gate_accepts_bodies_with_valid_markers():
    main = core.build_main_body("change-x", ("критерий",), "o/r")
    result = _gate(_sub_body(), main)
    assert result.ok, result.reasons


def test_gate_rejects_sub_issue_without_marker():
    main = core.build_main_body("change-x", ("критерий",), "o/r")
    body = _sub_body().replace(
        "<!-- issue-workflow:v1 role=sub change=change-x task=1.1 -->", ""
    )
    result = _gate(body, main)
    assert not result.ok
    assert any("маркер" in reason for reason in result.reasons)


def test_gate_rejects_foreign_change_id():
    main = core.build_main_body("change-x", ("критерий",), "o/r")
    result = _gate(_sub_body("other-change"), main)
    assert not result.ok
    assert any("change" in reason for reason in result.reasons)


def test_gate_rejects_unexpected_task_id():
    main = core.build_main_body("change-x", ("критерий",), "o/r")
    result = core.evaluate_gate(
        sub_issues=[{
            "number": 2,
            "title": "Задача",
            "state": "CLOSED",
            "url": "u",
            "body": _checked(_sub_body()),
        }],
        expected_count=1,
        main_body=_checked(main),
        checks={"pytest": True},
        expected_change_id="change-x",
        expected_task_ids=("9.9",),
    )
    assert not result.ok
    assert any("идентификаторы задач" in reason for reason in result.reasons)
