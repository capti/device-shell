from issue_workflow import github


class Result:
    returncode = 0
    stdout = "ok"
    stderr = ""


def test_run_passes_argument_list_without_shell(monkeypatch):
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return Result()

    monkeypatch.setattr(github.subprocess, "run", fake_run)

    assert github.run(["git", "status", "--porcelain"]) == "ok"
    assert captured["argv"] == ["git", "status", "--porcelain"]
    assert captured["kwargs"]["input"] is None


def test_run_raises_github_error_on_failure(monkeypatch):
    class Failed(Result):
        returncode = 1
        stderr = "permission denied"

    monkeypatch.setattr(github.subprocess, "run", lambda *a, **k: Failed())

    try:
        github.run(["gh", "issue", "close", "1"])
    except github.GitHubError as exc:
        assert "permission denied" in str(exc)
    else:
        raise AssertionError("ожидался GitHubError")


def test_get_issue_tree_follows_pagination(monkeypatch):
    def node(number):
        return {
            "number": number,
            "title": f"Задача {number}",
            "state": "CLOSED",
            "url": f"https://github.com/o/r/issues/{number}",
            "body": "тело",
        }

    first = {
        "repository": {
            "issue": {
                "body": "главный",
                "state": "OPEN",
                "subIssues": {
                    "nodes": [node(2)],
                    "pageInfo": {"hasNextPage": True, "endCursor": "CURSOR"},
                },
            }
        }
    }
    second = {
        "repository": {
            "issue": {
                "body": "главный",
                "state": "OPEN",
                "subIssues": {
                    "nodes": [node(3)],
                    "pageInfo": {"hasNextPage": False, "endCursor": "END"},
                },
            }
        }
    }
    calls = []
    pages = iter((first, second))

    def fake_graphql(query, variables):
        calls.append(variables)
        return next(pages)

    monkeypatch.setattr(github, "_graphql", fake_graphql)

    tree = github.get_issue_tree("o/r", 1)

    assert tree.main_body == "главный"
    assert [item.number for item in tree.subs] == [2, 3]
    assert "after" not in calls[0]
    assert calls[1]["after"] == "CURSOR"
