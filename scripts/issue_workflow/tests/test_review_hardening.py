"""Регрессионные тесты по результатам ревью: гейт и граница записи."""

import pytest
from issue_workflow import cli, core, github


def test_push_branch_rejects_main_and_foreign_branch(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("запрещённая ветка не должна попадать в git push")

    monkeypatch.setattr(github, "run", fail)
    for branch in ("main", "master", "feature/x"):
        with pytest.raises(github.GitHubError):
            github.push_branch(branch)


def test_push_branch_allows_change_branch(monkeypatch):
    calls = []
    monkeypatch.setattr(
        github, "run", lambda args, **kwargs: calls.append(args) or ""
    )
    github.push_branch("change/demo")
    assert calls == [("git", "push", "-u", "origin", "change/demo")]


def _manifest():
    return {
        "change_id": "demo",
        "repo": "o/r",
        "branch": "change/demo",
        "main_issue": {"number": 1},
        "subs": [{"task_id": "1.1"}],
    }


def test_finish_rechecks_local_checks_before_apply(monkeypatch):
    check_calls = []

    def checks(skip):
        check_calls.append(skip)
        return {}

    def gate(manifest, current, **kwargs):
        return core.GateResult(True, (), current)

    monkeypatch.setattr(cli, "_load_manifest", lambda cid: _manifest())
    monkeypatch.setattr(cli, "_local_checks", checks)
    monkeypatch.setattr(cli, "_gate", gate)
    monkeypatch.setattr(cli.github, "push_branch", lambda *a, **k: None)
    monkeypatch.setattr(cli.github, "create_pr", lambda *a, **k: "url")
    monkeypatch.setattr(cli.github, "close_issue", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_save_manifest", lambda *a, **k: None)

    assert cli.main(["finish", "--change-id", "demo", "--apply"]) == 0
    assert check_calls == [False, False]


def test_status_skip_checks_reports_incomplete(monkeypatch, capsys):
    seen = {}

    def gate(manifest, current, **kwargs):
        seen.update(kwargs)
        return core.GateResult(
            False, (), current, checks_complete=kwargs.get("checks_complete", True)
        )

    monkeypatch.setattr(cli, "_load_manifest", lambda cid: _manifest())
    monkeypatch.setattr(cli, "_local_checks", lambda skip: {})
    monkeypatch.setattr(cli, "_gate", gate)

    assert cli.main(["status", "--change-id", "demo", "--skip-checks"]) == 1
    assert seen["checks_complete"] is False
    assert "INCOMPLETE" in capsys.readouterr().out


def test_validate_sub_body_rejects_missing_section():
    body = core.build_sub_body(
        "demo",
        core.TaskSpec("1.1", "T"),
        main_number=1,
        role="subagent",
        scope="s",
        process=("p",),
        merge_gate="g",
    ).replace("### Handoff", "")
    assert any("секции" in reason for reason in core.validate_sub_body(body))


def _sub(number, task_id):
    body = core.build_sub_body(
        "demo",
        core.TaskSpec(task_id, "T"),
        main_number=1,
        role="subagent",
        scope="s",
        process=("p",),
        merge_gate="g",
        acceptance=("результат",),
    )
    return {
        "number": number,
        "title": "T",
        "state": "CLOSED",
        "url": "u",
        "body": body.replace("- [ ]", "- [x]"),
    }


def test_duplicate_task_ids_are_rejected():
    main = core.build_main_body("demo", ("критерий",), "o/r").replace(
        "- [ ]", "- [x]"
    )
    result = core.evaluate_gate(
        sub_issues=[_sub(2, "1.1"), _sub(3, "1.1")],
        expected_count=2,
        main_body=main,
        checks={"pytest": True},
        expected_change_id="demo",
        expected_task_ids=("1.1", "2.2"),
    )
    assert not result.ok
    assert any("идентификаторы задач" in reason for reason in result.reasons)


def test_already_closed_main_issue_is_rejected():
    main = core.build_main_body("demo", ("критерий",), "o/r").replace(
        "- [ ]", "- [x]"
    )
    result = core.evaluate_gate(
        sub_issues=[_sub(2, "1.1")],
        expected_count=1,
        main_body=main,
        checks={"pytest": True},
        expected_change_id="demo",
        expected_task_ids=("1.1",),
        main_state="CLOSED",
    )
    assert not result.ok
    assert any("уже закрыт" in reason for reason in result.reasons)


def test_report_shows_fail_for_non_bool_check():
    report = core.format_report(core.GateResult(False, (), {"pytest": 1}))
    assert "pytest: FAIL" in report
