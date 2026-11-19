import pytest
from issue_workflow import cli, core


def test_init_dry_run_makes_no_writes(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "_read_change",
        lambda cid: (["Критерий"], (core.TaskSpec("1.1", "Задача"),)),
    )

    def fail(*args, **kwargs):
        pytest.fail("dry-run не должен обращаться к GitHub")

    monkeypatch.setattr(cli.github, "create_issue", fail)
    monkeypatch.setattr(cli, "_save_manifest", fail)

    assert cli.main(["init", "--change-id", "demo", "--dry-run", "--repo", "o/r"]) == 0
    assert "DRY RUN" in capsys.readouterr().out


def test_status_returns_failure_code_with_reason(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "_load_manifest",
        lambda cid: {"repo": "o/r", "main_issue": {"number": 1}, "subs": [{}]},
    )
    monkeypatch.setattr(cli, "_local_checks", lambda skip: {"pytest": True})
    monkeypatch.setattr(
        cli,
        "_gate",
        lambda manifest, checks, **kwargs: core.GateResult(
            False, ("sub-issue #2 is OPEN",), checks
        ),
    )

    assert cli.main(["status", "--change-id", "demo", "--skip-checks"]) == 1
    assert "sub-issue #2 is OPEN" in capsys.readouterr().out


def test_finish_without_apply_is_read_only(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "_load_manifest",
        lambda cid: {"repo": "o/r", "main_issue": {"number": 1}, "subs": [{}]},
    )
    monkeypatch.setattr(cli, "_local_checks", lambda skip: {})
    monkeypatch.setattr(
        cli,
        "_gate",
        lambda manifest, checks, **kwargs: core.GateResult(True, (), checks),
    )

    def fail(*args, **kwargs):
        pytest.fail("finish без --apply не должен писать")

    for name in ("push_branch", "create_pr", "close_issue", "edit_issue_body"):
        monkeypatch.setattr(cli.github, name, fail)
    monkeypatch.setattr(cli, "_save_manifest", fail)

    assert cli.main(["finish", "--change-id", "demo"]) == 0
    assert "DRY RUN" in capsys.readouterr().out
