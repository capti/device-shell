"""Tests for marker constants, templates and the default process (no I/O)."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from issue_workflow import markers, templates


def test_marker_constants_exact_values():
    assert markers.METADATA_MARKER == "issue-workflow:v1"
    assert markers.CRITERIA_START == "<!-- workflow:criteria:start -->"
    assert markers.CRITERIA_END == "<!-- workflow:criteria:end -->"
    assert markers.ACCEPTANCE_START == "<!-- workflow:acceptance:start -->"
    assert markers.ACCEPTANCE_END == "<!-- workflow:acceptance:end -->"


def test_default_process_has_seven_non_empty_steps():
    assert len(templates.DEFAULT_PROCESS) == 7
    assert all(isinstance(step, str) and step for step in templates.DEFAULT_PROCESS)


def test_section_templates_are_non_empty_strings():
    names = (
        "SECTION_CRITERIA",
        "SECTION_SUB_ISSUES",
        "SECTION_ROLE",
        "SECTION_SCOPE",
        "SECTION_PROCESS",
        "SECTION_ACCEPTANCE",
        "SECTION_MERGE_GATE",
        "SECTION_EVIDENCE",
        "SECTION_HANDOFF",
    )
    for name in names:
        value = getattr(templates, name)
        assert isinstance(value, str) and value


def test_placeholders_and_part_of_template():
    assert templates.PART_OF_TEMPLATE.format(number=7) == "Part of #7"
    assert templates.BRANCH_TEMPLATE.format(change_id="c") == "Ветка: `change/c`"
    assert "#" in templates.EVIDENCE_PLACEHOLDER
