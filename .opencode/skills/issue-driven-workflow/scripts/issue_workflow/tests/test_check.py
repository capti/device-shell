"""Тесты явной отметки критериев: check --task / check --main и sync."""

from issue_workflow import cli, core, github, markers


def _body_with_checkboxes() -> str:
    return (
        "- [ ]Outside\n"
        f"{markers.CRITERIA_START}\n"
        "- [ ] критерий\n"
        f"{markers.CRITERIA_END}\n"
        "- [ ] снаружи\n"
    )


def test_mark_checklist_touches_only_marked_section():
    result = core.mark_checklist(
        _body_with_checkboxes(),
        markers.CRITERIA_START,
        markers.CRITERIA_END,
    )
    assert "- [x] критерий" in result
    assert result.count("- [ ]") == 2
    assert "- [ ]Outside" in result


def test_mark_checklist_raises_on_missing_markers():
    try:
        core.mark_checklist("нет маркеров", markers.CRITERIA_START, markers.CRITERIA_END)
    except core.MarkerError:
        pass
    else:
        raise AssertionError("ожидался MarkerError")


def _sub(number, state, task_id="1.1", accepted=True):
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
    if accepted:
        body = body.replace("- [ ]", "- [x]")
    return github.SubIssueState(number, "T", state, "u", body)


def _manifest():
    return {
        "change_id": "demo",
        "repo": "o/r",
        "branch": "change/demo",
        "criteria": ["критерий"],
        "main_issue": {"number": 1},
        "subs": [{"task_id": "1.1"}],
    }


def test_check_task_marks_acceptance(monkeypatch, capsys):
    tree = github.IssueTree("main", "OPEN", (_sub(2, "OPEN", accepted=False),))
    written = []
    monkeypatch.setattr(cli, "_load_manifest", lambda cid: _manifest())
    monkeypatch.setattr(cli.github, "get_issue_tree", lambda repo, number: tree)
    monkeypatch.setattr(
        cli.github, "edit_issue_body", lambda number, body: written.append((number, body))
    )

    assert cli.main(["check", "--change-id", "demo", "--task", "1.1"]) == 0
    assert written[0][0] == 2
    assert core.is_checklist_complete(
        written[0][1], markers.ACCEPTANCE_START, markers.ACCEPTANCE_END
    )
    assert "#2" in capsys.readouterr().out


def test_check_main_refuses_while_sub_is_open(monkeypatch):
    tree = github.IssueTree("main", "OPEN", (_sub(2, "OPEN"),))
    monkeypatch.setattr(cli, "_load_manifest", lambda cid: _manifest())
    monkeypatch.setattr(cli.github, "get_issue_tree", lambda repo, number: tree)

    def fail(*args, **kwargs):
        raise AssertionError("открытый sub-issue не должен позволять отметку")

    monkeypatch.setattr(cli.github, "edit_issue_body", fail)
    assert cli.main(["check", "--change-id", "demo", "--main"]) == 1


def test_check_main_marks_criteria_when_ready(monkeypatch):
    main_body = core.build_main_body("demo", ("критерий",), "o/r")
    tree = github.IssueTree(main_body, "OPEN", (_sub(2, "CLOSED"),))
    written = []
    monkeypatch.setattr(cli, "_load_manifest", lambda cid: _manifest())
    monkeypatch.setattr(cli.github, "get_issue_tree", lambda repo, number: tree)
    monkeypatch.setattr(
        cli.github, "edit_issue_body", lambda number, body: written.append((number, body))
    )

    assert cli.main(["check", "--change-id", "demo", "--main"]) == 0
    assert core.is_checklist_complete(
        written[0][1], markers.CRITERIA_START, markers.CRITERIA_END
    )


def test_sync_preserves_checked_criteria(monkeypatch):
    main_body = core.build_main_body("demo", ("критерий",), "o/r", criteria_checked=True)
    tree = github.IssueTree(main_body, "OPEN", (_sub(2, "CLOSED"),))
    written = []
    monkeypatch.setattr(cli, "_load_manifest", lambda cid: _manifest())
    monkeypatch.setattr(cli.github, "get_issue_tree", lambda repo, number: tree)
    monkeypatch.setattr(
        cli.github, "edit_issue_body", lambda number, body: written.append((number, body))
    )

    assert cli.main(["sync", "--change-id", "demo"]) == 0
    assert "- [x] критерий" in written[0][1]
