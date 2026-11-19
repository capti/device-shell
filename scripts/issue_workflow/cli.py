"""CLI issue-driven workflow: init, status, sync, finish."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import core, github

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / ".tmp" / "issues"
BACKEND = ROOT / "backend"
CHECKS: tuple[tuple[str, tuple[str, ...], Path], ...] = (
    ("pytest", ("uv", "run", "pytest", "-q"), BACKEND),
    ("ruff", ("uv", "run", "ruff", "check", "."), BACKEND),
    ("openspec", ("openspec", "validate", "--all", "--strict"), ROOT),
)
DEFAULT_GATE = (
    "Все критерии приёмки отмечены, проверки зелёные, sub-issue закрыт."
)


def _manifest_path(change_id: str) -> Path:
    return MANIFESTS / f"{change_id}.json"


def _load_manifest(change_id: str) -> dict[str, Any]:
    path = _manifest_path(change_id)
    if not path.exists():
        raise SystemExit(f"Манифест не найден: {path}. Сначала выполните init.")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_manifest(change_id: str, data: dict[str, Any]) -> None:
    path = _manifest_path(change_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _extract_criteria(proposal: str) -> list[str]:
    lines = proposal.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == "## What Changes"),
        None,
    )
    if start is None:
        raise SystemExit("В proposal.md нет раздела '## What Changes'")
    result: list[str] = []
    buffer: list[str] = []
    for line in lines[start + 1:]:
        stripped = line.strip()
        if stripped.startswith("### "):
            break
        if stripped.startswith("- "):
            if buffer:
                result.append(" ".join(buffer))
            buffer = [stripped[2:].strip()]
        elif buffer and stripped:
            buffer.append(stripped)
    if buffer:
        result.append(" ".join(buffer))
    return result


def _read_change(change_id: str) -> tuple[list[str], tuple[core.TaskSpec, ...]]:
    folder = ROOT / "openspec" / "changes" / change_id
    if not folder.is_dir():
        raise SystemExit(f"Change не найден: {folder}")
    proposal = (folder / "proposal.md").read_text(encoding="utf-8")
    tasks = (folder / "tasks.md").read_text(encoding="utf-8")
    return _extract_criteria(proposal), tuple(core.parse_task_specs(tasks))


def _sub_body(
    change_id: str, task: core.TaskSpec, main_number: int, gate: str
) -> str:
    return core.build_sub_body(
        change_id=change_id,
        task=task,
        main_number=main_number,
        role="subagent",
        scope=task.title,
        process=core.DEFAULT_PROCESS,
        merge_gate=gate,
        handoff="Передать результат в главный issue и дождаться гейта.",
        acceptance=core.DEFAULT_ACCEPTANCE,
    )


def _tree_dicts(tree: github.IssueTree) -> list[dict[str, Any]]:
    return [
        {
            "number": item.number,
            "title": item.title,
            "state": item.state,
            "url": item.url,
            "body": item.body,
        }
        for item in tree.subs
    ]


def cmd_init(args: argparse.Namespace) -> int:
    change_id = args.change_id
    if _manifest_path(change_id).exists():
        raise SystemExit("Манифест уже есть — используйте status, init не создаёт дубликаты.")
    criteria, specs = _read_change(change_id)
    if not specs:
        raise SystemExit("В tasks.md не найдено задач формата '- [ ] 1.1 ...'")
    repo = args.repo or github.get_repo()
    body = core.build_main_body(change_id, criteria, repo)
    if args.dry_run:
        print("DRY RUN — записей в GitHub нет.")
        print(body)
        for spec in specs:
            print(f"\n--- SUB {spec.task_id} ---\n{_sub_body(change_id, spec, 0, DEFAULT_GATE)}")
        return 0
    main = github.create_issue(
        f"[change] {change_id}", body, labels=("workflow", "change", "backlog")
    )
    subs: list[dict[str, Any]] = []
    for spec in specs:
        body = _sub_body(change_id, spec, main.number, DEFAULT_GATE)
        errors = core.validate_sub_body(body)
        if errors:
            raise SystemExit(
                f"некорректное тело sub-issue {spec.task_id}: {'; '.join(errors)}"
            )
        issue = github.create_issue(
            f"{spec.task_id}: {spec.title}",
            body,
            labels=("workflow", "subagent", "backlog"),
            parent=main.number,
        )
        subs.append({
            "task_id": spec.task_id,
            "number": issue.number,
            "url": issue.url,
            "title": spec.title,
        })
    _save_manifest(change_id, {
        "change_id": change_id,
        "repo": repo,
        "branch": f"change/{change_id}",
        "criteria": criteria,
        "main_issue": {"number": main.number, "url": main.url},
        "subs": subs,
    })
    print(f"Главный issue #{main.number}; sub-issues: {len(subs)}")
    return 0


def _local_checks(skip: bool) -> dict[str, bool]:
    if skip:
        return {}
    checks: dict[str, bool] = {}
    for name, command, cwd in CHECKS:
        try:
            github.run(command, cwd=cwd)
            checks[name] = True
        except github.GitHubError as exc:
            checks[name] = False
            print(f"Проверка {name} не пройдена: {exc}", file=sys.stderr)
    try:
        checks["git-clean"] = github.is_worktree_clean()
    except github.GitHubError:
        checks["git-clean"] = False
    return checks


def _gate(
    manifest: dict[str, Any],
    checks: dict[str, bool],
    *,
    checks_complete: bool = True,
) -> core.GateResult:
    tree = github.get_issue_tree(manifest["repo"], manifest["main_issue"]["number"])
    return core.evaluate_gate(
        sub_issues=_tree_dicts(tree),
        expected_count=len(manifest["subs"]),
        main_body=tree.main_body,
        checks=checks,
        expected_change_id=manifest["change_id"],
        expected_task_ids=[sub["task_id"] for sub in manifest["subs"]],
        checks_complete=checks_complete,
        main_state=tree.main_state,
    )


def cmd_status(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.change_id)
    checks = _local_checks(args.skip_checks)
    result = _gate(manifest, checks, checks_complete=not args.skip_checks)
    print(core.format_report(result))
    return 0 if result.ok else 1


def cmd_sync(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.change_id)
    tree = github.get_issue_tree(manifest["repo"], manifest["main_issue"]["number"])
    body = core.build_main_body(
        args.change_id,
        manifest["criteria"],
        manifest["repo"],
        sub_issues=_tree_dicts(tree),
    )
    number = manifest["main_issue"]["number"]
    github.edit_issue_body(number, body)
    print(f"Чеклист главного issue #{number} обновлён")
    return 0


def cmd_finish(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.change_id)
    # Финал всегда прогоняет полный набор проверок: --skip-checks ослаблял бы гейт.
    checks = _local_checks(False)
    result = _gate(manifest, checks)
    print(core.format_report(result))
    if not args.apply:
        print("DRY RUN: --apply только после явного подтверждения пользователя.")
        return 0 if result.ok else 1
    if not result.ok:
        return 1
    repeat = _gate(manifest, _local_checks(False))
    if not repeat.ok:
        print("Гейт изменился после проверки — записей не производится.")
        print(core.format_report(repeat))
        return 1
    number = manifest["main_issue"]["number"]
    branch = manifest["branch"]
    github.push_branch(branch)
    pr_url = github.create_pr(
        f"[{args.change_id}] Issue-driven workflow",
        f"Implements #{number}\n\n{core.format_report(repeat)}",
        branch,
    )
    github.close_issue(number, "issue-driven workflow: гейт пройден")
    manifest["closed_at"] = datetime.now(UTC).isoformat()
    manifest["pr_url"] = pr_url
    _save_manifest(args.change_id, manifest)
    print(f"PR: {pr_url}")
    return 0


SUBCOMMANDS: dict[str, Callable[[argparse.Namespace], int]] = {
    "init": cmd_init,
    "status": cmd_status,
    "sync": cmd_sync,
    "finish": cmd_finish,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="issue-workflow",
        description="Issue-driven execution of OpenSpec changes",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, handler in SUBCOMMANDS.items():
        command = commands.add_parser(name)
        command.add_argument("--change-id", required=True)
        if name == "init":
            command.add_argument("--dry-run", action="store_true")
            command.add_argument("--repo")
        if name == "status":
            command.add_argument("--skip-checks", action="store_true")
        if name == "finish":
            command.add_argument("--apply", action="store_true")
        command.set_defaults(handler=handler)
    args = parser.parse_args(argv)
    return args.handler(args)
