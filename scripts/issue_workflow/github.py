"""Тонкие обёртки над gh CLI и git.

Тела issue и комментарии — недоверенные данные: они передаются только через
stdin или как элементы списка аргументов и никогда не интерпретируются как
команды. Вся проверка содержимого живёт в core.py.
"""
from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

GRAPHQL_TREE = """
query($owner:String!,$name:String!,$number:Int!,$after:String) {
  repository(owner:$owner, name:$name) {
    issue(number:$number) {
      id
      state
      body
      subIssues(first:100, after:$after) {
        nodes { number title state url body }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""


class GitHubError(RuntimeError):
    """Ошибка вызова gh или git."""


@dataclass(frozen=True)
class IssueRef:
    number: int
    url: str
    title: str


@dataclass(frozen=True)
class SubIssueState:
    number: int
    title: str
    state: str
    url: str
    body: str


@dataclass(frozen=True)
class IssueTree:
    main_body: str
    main_state: str
    subs: tuple[SubIssueState, ...]


def run(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
) -> str:
    """Выполнить команду списком аргументов, вернуть stdout или GitHubError."""
    argv = list(args)
    result = subprocess.run(
        argv,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        raise GitHubError(f"{' '.join(argv[:3])}: {detail}")
    return result.stdout.strip()


def get_repo() -> str:
    """Вернуть repo в формате owner/name через gh repo view."""
    return run((
        "gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"
    ))


def create_issue(
    title: str,
    body: str,
    *,
    labels: Sequence[str] = (),
    parent: int | None = None,
) -> IssueRef:
    """Создать issue; тело передаётся через stdin, связь — через --parent."""
    args = ["gh", "issue", "create", "--title", title, "--body-file", "-"]
    if labels:
        args.extend(["--label", ",".join(labels)])
    if parent is not None:
        args.extend(["--parent", str(parent)])
    url = run(args, input_text=body)
    return IssueRef(int(url.rstrip("/").rsplit("/", 1)[-1]), url, title)


def _graphql(query: str, variables: dict[str, str]) -> dict:
    args = ["gh", "api", "graphql"]
    for key, value in variables.items():
        args.extend(["-F", f"{key}={value}"])
    args.extend(["-f", f"query={query}"])
    return json.loads(run(args))


def get_issue_tree(repo: str, main_number: int) -> IssueTree:
    """Прочитать главный issue и все его sub-issues с пагинацией."""
    owner, name = repo.split("/", 1)
    subs: list[SubIssueState] = []
    cursor = ""
    main_body = ""
    main_state = ""
    while True:
        variables = {"owner": owner, "name": name, "number": str(main_number)}
        if cursor:
            variables["after"] = cursor
        issue = _graphql(GRAPHQL_TREE, variables)["repository"]["issue"]
        if issue is None:
            raise GitHubError(f"issue #{main_number} не найден в {repo}")
        main_body = issue["body"] or ""
        main_state = issue["state"]
        connection = issue["subIssues"]
        subs.extend(
            SubIssueState(
                number=node["number"],
                title=node["title"],
                state=node["state"],
                url=node["url"],
                body=node["body"] or "",
            )
            for node in connection["nodes"]
        )
        page = connection["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]
    return IssueTree(main_body, main_state, tuple(subs))


def edit_issue_body(number: int, body: str) -> None:
    """Перезаписать тело issue через stdin."""
    run(("gh", "issue", "edit", str(number), "--body-file", "-"), input_text=body)


def close_issue(number: int, comment: str) -> None:
    """Закрыть issue с комментарием-основанием."""
    run((
        "gh", "issue", "close", str(number),
        "--comment", comment, "--reason", "completed",
    ))


def push_branch(branch: str) -> None:
    """Отправить feature-ветку в origin; в main/master пуш запрещён."""
    if branch in ("main", "master") or not branch.startswith("change/"):
        raise GitHubError(f"пуш ветки '{branch}' запрещён: ожидается change/<id>")
    run(("git", "push", "-u", "origin", branch))


def create_pr(title: str, body: str, head: str, base: str = "main") -> str:
    """Открыть PR; Implements #N в теле не закрывает issue автоматически."""
    return run((
        "gh", "pr", "create", "--head", head, "--base", base,
        "--title", title, "--body-file", "-",
    ), input_text=body)


def is_worktree_clean() -> bool:
    """Локальные изменения отсутствуют."""
    return run(("git", "status", "--porcelain")) == ""
