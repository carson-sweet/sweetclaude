import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[1]
DOCTOR = REPO_ROOT / "scripts" / "doctor.py"
DOCTOR_SKILL = REPO_ROOT / "skill-library" / "configure" / "doctor" / "SKILL.md"
SYNCOG_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "syncog-layout"
MIGRATE_SMOKE = REPO_ROOT / "tests" / "fixtures" / "migrate-smoke"

TYPED_CAPABILITY = "migrate.typed_legacy_backlog"
FLAT_CAPABILITY = "migrate.flat_bl_to_issue"


def _typed_legacy_project(tmp_path: Path) -> Path:
    project = tmp_path / "typed"
    shutil.copytree(SYNCOG_FIXTURE, project)
    state_dir = project / ".sweetclaude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (project / ".sweetclaude" / "artifact-privacy.yaml").write_text(
        "schema_version: 1\ncategories:\n  product:\n    privacy: private\n    base_path: docs/product\n",
        encoding="utf-8",
    )
    (state_dir / "sweetclaude.yaml").write_text(
        yaml.safe_dump({
            "framework": {"installed_version": "4.2.5-beta", "migration_status": "deferred"},
            "paths": {"product_base": "docs/product"},
            "recovery": {
                "taxonomy": {
                    "status": "stabilized-without-migration",
                    "migration_required": False,
                    "blind_taxonomy_migration_allowed": False,
                },
            },
        }),
        encoding="utf-8",
    )
    return project


def _flat_bl_project(tmp_path: Path) -> Path:
    project = tmp_path / "flat"
    shutil.copytree(MIGRATE_SMOKE, project)
    return project


def _route(project: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(DOCTOR), "maintenance-route", "--project-dir", str(project)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["maintenance_route"]


def _supported_migration_section() -> str:
    text = DOCTOR_SKILL.read_text(encoding="utf-8")
    start = text.index("If `maintenance_route.status` is `supported-migration-available`")
    end = text.index("If `maintenance_route.status` is `graduation-available`")
    return text[start:end]


def _prompts(section: str) -> list[tuple[int, str]]:
    return [
        (match.start(), " ".join(line.lstrip("> ").strip() for line in match.group(0).splitlines()))
        for match in re.finditer(r"(?:^>.*\n?)+", section, re.M)
    ]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def _prompt_for(section: str, capability_id: str, layout_phrase: str) -> str | None:
    other = FLAT_CAPABILITY if capability_id == TYPED_CAPABILITY else TYPED_CAPABILITY
    for position, prompt in _prompts(section):
        if layout_phrase not in _normalize(prompt):
            continue
        before = section[:position]
        if before.rfind(capability_id) > before.rfind(other):
            return prompt
    return None


class TestR207DoctorMigrationPromptNamesLayout:
    def test_typed_legacy_fixture_routes_to_typed_legacy_capability(self, tmp_path):
        route = _route(_typed_legacy_project(tmp_path))

        assert route["status"] == "supported-migration-available"
        assert route["primary_action"]["capability_id"] == TYPED_CAPABILITY
        assert TYPED_CAPABILITY in _supported_migration_section()

    def test_typed_legacy_prompt_names_typed_legacy_layout(self, tmp_path):
        route = _route(_typed_legacy_project(tmp_path))
        capability_id = route["primary_action"]["capability_id"]

        prompt = _prompt_for(_supported_migration_section(), capability_id, "typed legacy")

        assert prompt is not None, "no prompt gated on the typed legacy capability names the typed legacy layout"
        assert "flat bl-nnn" not in _normalize(prompt)

    def test_flat_bl_prompt_names_flat_bl_layout(self, tmp_path):
        route = _route(_flat_bl_project(tmp_path))
        capability_id = route["primary_action"]["capability_id"]

        assert route["status"] == "supported-migration-available"
        assert capability_id == FLAT_CAPABILITY
        prompt = _prompt_for(_supported_migration_section(), capability_id, "flat bl-nnn")

        assert prompt is not None, "no prompt gated on the flat BL capability names the flat BL-NNN layout"

    def test_no_unconditional_flat_bl_claim_for_every_candidate(self):
        section = _supported_migration_section()
        flat_positions = [pos for pos, p in _prompts(section) if "flat bl-nnn" in _normalize(p)]

        assert flat_positions
        for position in flat_positions:
            assert FLAT_CAPABILITY in section[:position], (
                "flat BL-NNN prompt is shown without being gated on the flat BL capability"
            )
