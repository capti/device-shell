"""Text templates and the default process for issue bodies.

Only :mod:`markers` is imported here. Strings live in one place so that body
builders in ``core`` stay small and the section titles can be asserted in tests.
"""

from . import markers

METADATA_MARKER = markers.METADATA_MARKER

# Section titles (Russian - they are shown to humans in GitHub).
SECTION_CRITERIA = "### Критерии change"
SECTION_SUB_ISSUES = "### Связанные sub-issues"
SECTION_ROLE = "### Роль и владелец (owner)"
SECTION_SCOPE = "### Scope (границы задачи)"
SECTION_PROCESS = "### Процесс от начала до конца"
SECTION_ACCEPTANCE = "### Критерии приёмки"
SECTION_MERGE_GATE = "### Условие интеграции (merge gate)"
SECTION_EVIDENCE = "### Доказательства (evidence)"
SECTION_HANDOFF = "### Handoff"

# Line templates.
BRANCH_TEMPLATE = "Ветка: `change/{change_id}`"
REPO_TEMPLATE = "Репозиторий: `{repo}`"
SUMMARY_TEMPLATE = "Кратко: {summary}"
PART_OF_TEMPLATE = "Part of #{number}"
ROLE_TEMPLATE = "Роль: {role}\nВетка: `change/{change_id}`\nWorktree: управляется devfleet"
EVIDENCE_PLACEHOLDER = (
    "- [ ] Доказательства приложены (вывод тестов, линтера, ссылки на артефакты, коммит #<sha>)"
)
HANDOFF_PLACEHOLDER = "_Заполняется при передаче результата._"

# Acceptance criteria are outcomes, not process steps: the gate must require
# results, not merely that the agent walked through the motions.
DEFAULT_ACCEPTANCE = (
    "Задача реализована и соответствует формулировке из tasks.md",
    "Падающий тест написан и исправлен минимальным фиксом",
    "ruff и pytest зелёные, UB-инструменты прогоняются по рецепту AGENTS.md",
    "Локальный коммит Conventional Commits создан (без пуша)",
    "Доказательства приложены в раздел evidence",
)

# The full, start-to-finish process of a sub-agent (7 steps).
DEFAULT_PROCESS = (
    "Прочитать OpenSpec-контекст change и связанные инварианты",
    "Реализовать задачу строго по её формулировке",
    "Написать падающий тест и сделать минимальный фикс до зелёного",
    "Прогнать ruff/pytest и crapper/dryer/mutator",
    "Сделать локальный коммит Conventional Commits (без пуша)",
    "Приложить доказательства (evidence) и отметить чеклист",
    "Передать результат в handoff оркестратору",
)
