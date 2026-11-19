"""PR связывает issue через Closes #N и закрывает его только при мерже."""

import pytest
from issue_workflow import cli, core, github


def _manifest():
    return {
        "change_id": "demo",
        "repo": "o/r",
        "branch": "change/demo",
        "main_issue": {"number": 1},
        "subs": [{"task_id": "1.1"}],
    }


def test_finish_creates_closing_pr_in_default_branch(monkeypatch):
    captured = {}
    saved = {}

    monkeypatch.setattr(cli, "_load_manifest", lambda cid: _manifest())
    monkeypatch.setattr(cli, "_local_checks", lambda skip: {})
    monkeypatch.setattr(
        cli, "_gate", lambda manifest, checks: core.GateResult(True, (), checks)
    )
    monkeypatch.setattr(cli.github, "push_branch", lambda branch: None)
    monkeypatch.setattr(cli.github, "get_default_branch", lambda repo: "trunk")

    def create_pr(title, body, head, base):
        captured.update(title=title, body=body, head=head, base=base)
        return "https://github.com/o/r/pull/9"

    monkeypatch.setattr(cli.github, "create_pr", create_pr)
    monkeypatch.setattr(
        cli.github,
        "close_issue",
        lambda *a, **k: pytest.fail("issue не должен закрываться до мержа PR"),
    )
    monkeypatch.setattr(
        cli, "_save_manifest", lambda cid, data: saved.update(data)
    )

    assert cli.main(["finish", "--change-id", "demo", "--apply"]) == 0
    assert "Closes #1" in captured["body"]
    assert "Implements" not in captured["body"]
    assert captured["head"] == "change/demo"
    assert captured["base"] == "trunk"
    assert saved["pr_base"] == "trunk"
    assert saved["pr_url"] == "https://github.com/o/r/pull/9"


def test_get_default_branch_queries_graphql(monkeypatch):
    monkeypatch.setattr(
        github,
        "_graphql",
        lambda query, variables: {
            "repository": {"defaultBranchRef": {"name": "trunk"}}
        },
    )
    assert github.get_default_branch("o/r") == "trunk"


def test_get_default_branch_rejects_empty_ref(monkeypatch):
    monkeypatch.setattr(
        github,
        "_graphql",
        lambda query, variables: {"repository": {"defaultBranchRef": None}},
    )
    with pytest.raises(github.GitHubError):
        github.get_default_branch("o/r")
