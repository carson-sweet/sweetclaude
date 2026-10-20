from pathlib import Path


def test_recover_skill_delegates_to_recovery_script_and_keeps_safety_gates():
    skill = (Path(__file__).parents[1] / "skill-library" / "configure" / "recover" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "/sweetclaude:configure recover" in skill
    assert "Default user entrypoint: `/sweetclaude:configure recover`" in skill
    assert "No argument is required" in skill
    assert "scripts/recovery/recover_project.py" in skill
    assert "diagnose --project-dir . --pretty" in skill
    assert "plan --project-dir . --pretty" in skill
    assert "mutation_plan" in skill
    assert "approval_receipt_template" in skill
    assert "execute --project-dir . --approve --approval-receipt" in skill
    assert "resume --run-dir" in skill
    assert "rollback --run-dir" in skill
    assert "Never run `sweetclaude:library-load migrate`" in skill
    assert "Never move, rename, delete, or normalize product artifacts manually" in skill
    assert ".sweetclaude/state/recovery-runs/" in skill


def test_setup_skill_ignores_recovery_run_artifacts_by_default():
    skill = (Path(__file__).parents[1] / "skill-library" / "configure" / "setup" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "Keep recovery snapshots and manifests out of source control" in skill
    assert ".sweetclaude/state/recovery-runs/" in skill


def test_status_skill_routes_unsafe_layouts_to_recover_not_migrate():
    skill = (Path(__file__).parents[1] / "skills" / "status" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "guard --project-dir . --pretty" in skill
    assert "Run /sweetclaude:configure recover" in skill
    assert "Do not run /sweetclaude:configure migrate yet" in skill
    assert "run `/sweetclaude:configure migrate` first" not in skill


def test_legacy_project_skills_use_recovery_guard_before_migration():
    root = Path(__file__).parents[1]
    guarded_skills = [
        ("skills", None, "bootstrap"), ("skills", None, "go"),
        ("skill-library", "build", "project-backlog"),
        ("skill-library", "build", "project-backlog-triage"),
        ("skill-library", "build", "project-gh-import-issues"),
        ("skill-library", "build", "project-gh-sync-issues"),
        ("skill-library", "build", "project-issues"),
    ]

    for collection, category, name in guarded_skills:
        base = root / collection if category is None else root / collection / category
        skill = (base / name / "SKILL.md").read_text(encoding="utf-8")
        assert "guard --project-dir ." in skill
        assert "/sweetclaude:configure recover" in skill
        assert "Run: /sweetclaude:configure migrate" not in skill


def test_bootstrap_v4_hard_stop_classifies_before_recommending_migrate():
    skill = (
        Path(__file__).parents[1] / "skills" / "bootstrap" / "SKILL.md"
    ).read_text(encoding="utf-8")

    guard_idx = skill.index("guard --project-dir .")
    migrate_idx = skill.index(
        "Recommend `/sweetclaude:configure migrate` for statuses"
    )
    assert guard_idx < migrate_idx, (
        "the guard must classify the project before any migrate recommendation"
    )
    assert "sweetclaude:library-load recover" in skill
    assert "`migration-may-be-needed`" in skill
    assert "graduation-blocked" in skill, (
        "bootstrap must route blocked graduation, not dead-end it"
    )
    assert "LEGACY_FILES" in skill, (
        "advisory mode must also trigger on legacy-taxonomy files when state "
        "claims migration is complete (state/artifact disagreement)"
    )


def test_migrate_skill_runs_preflight_before_lock_and_backup():
    skill = (Path(__file__).parents[1] / "skill-library" / "configure" / "migrate" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    preflight_idx = skill.index("preflight --project-dir .")
    assert preflight_idx < skill.index('LOCK_FILE=".sweetclaude/state/migration.lock"')
    assert preflight_idx < skill.index('BACKUP_DIR=".sweetclaude/state/backups"')
    assert "Do not create `migration.lock`, backups, copied files, or migration maps" in skill


def test_doctor_skill_does_not_directly_run_taxonomy_migration():
    skill = (Path(__file__).parents[1] / "skill-library" / "configure" / "doctor" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "migrate_taxonomy.py" in skill
    assert "Do not invoke\n`migrate_taxonomy.py`" in skill
    assert "run the script directly" not in skill.lower()


def test_doctor_skill_uses_maintenance_router_as_front_door():
    skill = (Path(__file__).parents[1] / "skill-library" / "configure" / "doctor" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "doctor.py maintenance-route --project-dir ." in skill
    assert "Store `maintenance_route`. Doctor is the maintenance front door" in skill
    assert "Run safe recovery" in skill
    assert "Start supported migration" in skill
    assert "No migration is recommended for this project" in skill
    assert "compatibility_adjustments" in skill
    assert "Compatibility mode collapsed {collapsed_count} accepted legacy taxonomy" in skill
    assert "Do not `cat` or print\n`.sweetclaude/state/last-doctor-run.json`" in skill
    assert "Use `menu_default` for skip-menu behavior" in skill
    assert "must not skip the menu by itself" in skill
    assert "Continue in compatibility mode" not in skill
    assert "internal commands such as `recover`,\n`_migrate`" in skill
    assert "Step 1 must already have handled and visibly rendered" in skill
    assert "Do not use it to\npresent a migration prompt unless `maintenance_route.status` is\n`supported-migration-available`" in skill


def test_update_skill_decouples_framework_sync_from_project_mutation():
    skill = (Path(__file__).parents[1] / "skill-library" / "configure" / "update" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    capability = (
        Path(__file__).parents[1]
        / "skill-library"
        / "configure"
        / "update"
        / "capability-surface.md"
    ).read_text(encoding="utf-8")

    # B2 contract anchors (ISSUE-234, decision log #32). These exact sentences
    # are grep-anchored by recover_project.py's _update_skill_contract_check —
    # rewording them requires updating the check's required list and this test
    # in the same change.
    assert "Update never mutates project work-item state." in skill
    assert "Update does not run project-state migrations inline" in skill
    assert "Do not present a migration prompt from update." in skill
    assert "Do not write `doctor-prompt-pending.json` from update." in skill

    assert "No project files were changed by update." in skill
    assert "invoke `sweetclaude:_migrate`" not in skill
    assert "invoke `sweetclaude:purge`" not in skill
    assert "invoke `sweetclaude:adopt`" not in skill
    assert "mv .sweetclaude" not in skill
    assert "configure-plan-dir.py" not in skill
    assert "Both parts must execute" not in capability
    assert "disabled from update" in capability
    assert "Do not execute these\ncommands from update" in capability


def test_fix_sweetclaude_is_redirect_only():
    skill = (
        Path(__file__).parents[1] / "skill-library" / "configure" / "fix-sweetclaude" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "replaced by `/sweetclaude:configure doctor`" in skill
    assert "Invoke `sweetclaude:library-load doctor` now." in skill
    assert "python3" not in skill
    assert "rm " not in skill
    assert "mv " not in skill
    assert "migrate_taxonomy.py" not in skill


def test_user_docs_route_to_no_arg_recover_not_diagnose_subcommand():
    root = Path(__file__).parents[1]
    docs = [
        root / "README.md",
        root / "docs" / "user-guide" / "install.md",
        root / "docs" / "user-guide" / "beta-rescue.md",
        root / "docs" / "user-guide" / "skills-reference.md",
    ]

    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert "/sweetclaude:configure recover diagnose" not in text

    rescue = (root / "docs" / "user-guide" / "beta-rescue.md").read_text(encoding="utf-8")
    assert "/sweetclaude:configure recover" in rescue
    assert "Recovery diagnoses first" in rescue


def test_stale_beta_plugin_guard_is_front_door_for_update_bootstrap_and_doctor():
    """Three-legged guard (ISSUE-234): bootstrap and doctor consume
    preflight.sh's SC_PLUGIN_STALE_BETA env var; update consumes update.py
    preflight's stale_beta_install JSON key; both come from the single
    producer scripts/maintenance/plugin-state.py. All three legs must stop
    with the same message before any project mutation."""
    root = Path(__file__).parents[1]

    for rel in [
        "skills/bootstrap/SKILL.md",
        "skill-library/configure/doctor/SKILL.md",
    ]:
        text = (root / rel).read_text(encoding="utf-8")
        assert "SC_PLUGIN_STALE_BETA=true" in text, rel
        assert "SweetClaude beta plugin update required" in text, rel
        assert "{SC_PLUGIN_UPDATE_COMMAND}" in text, rel
        assert "Then restart Claude Code and run:" in text, rel
        assert "/sweetclaude:configure update" in text, rel
        assert "No project files were changed" in text, rel

    update = (root / "skill-library/configure/update/SKILL.md").read_text(encoding="utf-8")
    assert "stale_beta_install" in update
    assert "SweetClaude beta plugin update required" in update
    assert "Then restart Claude Code and run:" in update
    assert "/sweetclaude:configure update" in update
    assert "No project files were changed" in update

    producer = (root / "scripts/maintenance/plugin-state.py").read_text(
        encoding="utf-8"
    )
    assert '"stale_beta_install"' in producer
    assert '"SC_PLUGIN_STALE_BETA"' in producer

    doctor = (root / "skill-library/configure/doctor/SKILL.md").read_text(encoding="utf-8")
    assert doctor.index("Plugin Update Guard") < doctor.index("Maintenance route preflight")

    bootstrap = (root / "skills/bootstrap/SKILL.md").read_text(encoding="utf-8")
    assert bootstrap.index("SC_PLUGIN_STALE_BETA=true") < bootstrap.index("Handle missing or unparseable file")

    assert update.index("stale_beta_install") < update.index("Present current state")


def test_update_skill_does_not_invoke_orphan_mutations():
    """ISSUE-235 (boundary B2): update never mutates work-item state. The
    orphan-resolution actions live behind doctor; update only reports
    orphan_count and routes there."""
    root = Path(__file__).resolve().parent.parent
    text = (root / "skill-library/configure/update/SKILL.md").read_text(encoding="utf-8")
    for mutating_subcommand in (
        "reonboard-orphans",
        "archive-orphans",
        "acknowledge-orphans",
        "resolve-orphan",
        "group-orphans",
    ):
        assert mutating_subcommand not in text, (
            f"update SKILL.md must not invoke {mutating_subcommand}"
        )
    assert "orphan" in text.lower(), (
        "update must still report orphan_count and route to doctor"
    )
    assert "doctor" in text.lower()


def test_doctor_skill_documents_orphan_resolution():
    """ISSUE-235: doctor owns the orphan-resolution flow — its skill must
    instruct the model to present the action menu and execute through the
    resolve_orphans executor action (archived, reversible)."""
    root = Path(__file__).resolve().parent.parent
    text = (root / "skill-library/configure/doctor/SKILL.md").read_text(encoding="utf-8")
    assert "resolve_orphans" in text, (
        "doctor SKILL.md must handle the resolve_orphans prompted recipe"
    )
    for option in ("cknowledge", "rchive", "e-onboard"):
        assert option in text, (
            f"orphan resolution menu must offer {option!r}"
        )


def test_update_skill_contract_check_passes_on_repo():
    """ISSUE-234: the recovery postcondition's required anchors must exist in
    the shipped update skill — this is the unit half of the guard whose
    integration half is test_recovery_execute_project.py."""
    from recovery.recover_project import _update_skill_contract_check

    result = _update_skill_contract_check()
    assert result["status"] == "passed", result["missing_phrases"]


def test_update_skill_contract_check_fails_when_anchor_removed(tmp_path):
    """Removing any single anchor sentence must fail the check and name the
    missing phrase — the recurrence guard for prose/check drift."""
    from recovery.recover_project import _update_skill_contract_check

    repo = Path(__file__).parents[1]
    original = (repo / "skill-library/configure/update/SKILL.md").read_text(encoding="utf-8")

    result = _update_skill_contract_check()
    assert result["status"] == "passed"
    required_now = [
        "Update never mutates project work-item state.",
        "Update does not run project-state migrations inline",
        "Do not present a migration prompt from update.",
        "Do not write `doctor-prompt-pending.json` from update.",
    ]
    for anchor in required_now:
        assert anchor in original, f"repo skill must contain anchor {anchor!r}"
        mutated_root = tmp_path / f"root-{required_now.index(anchor)}"
        skill_dir = mutated_root / "skill-library" / "configure" / "update"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            original.replace(anchor, ""), encoding="utf-8"
        )
        result = _update_skill_contract_check(root=mutated_root)
        assert result["status"] == "failed", (
            f"check must fail when anchor {anchor!r} is removed"
        )
        assert any(anchor.startswith(m) or m.startswith(anchor)
                   for m in result["missing_phrases"]), result["missing_phrases"]


def test_update_script_contract_markers_pass_on_repo():
    """ISSUE-234 (A2 leg): code-behavior markers — update.py carries no
    doctor-prompt writes and no mutating orphan subcommands; plugin-state.py
    is the single stale-beta producer for all three entrypoint legs."""
    from recovery.recover_project import _update_script_contract_check

    result = _update_script_contract_check()
    assert result["id"] == "update-script-contract-markers"
    assert result["status"] == "passed", result


def test_update_script_contract_markers_fail_on_forbidden_marker(tmp_path):
    from recovery.recover_project import _update_script_contract_check

    repo = Path(__file__).parents[1]
    scripts = tmp_path / "scripts"
    (scripts / "maintenance").mkdir(parents=True)
    bad_update = (repo / "scripts/update.py").read_text(encoding="utf-8") + (
        '\n# smuggled: subprocess.run(["acknowledge-orphans"])\n'
    )
    (scripts / "update.py").write_text(bad_update, encoding="utf-8")
    (scripts / "maintenance" / "plugin-state.py").write_text(
        (repo / "scripts/maintenance/plugin-state.py").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    result = _update_script_contract_check(root=tmp_path)
    assert result["status"] == "failed"
    assert any("acknowledge-orphans" in str(v) for v in result.values()), result


def test_maintenance_entrypoint_checks_include_script_markers(tmp_path):
    """The A2 marker check must roll up into maintenance-entrypoints-safe via
    _maintenance_entrypoint_checks like the prose checks do."""
    from recovery.recover_project import _maintenance_entrypoint_checks

    repo = Path(__file__).parents[1]
    checks = _maintenance_entrypoint_checks(repo)
    ids = {c["id"] for c in checks}
    assert "update-skill-taxonomy-prompt-disabled" in ids
    assert "update-script-contract-markers" in ids
