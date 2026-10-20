#!/usr/bin/env python3
"""Execute a capability's declared postcondition against a fixture project.

Every capability in config/capability-manifest.yaml declares a postcondition
in prose. Until ISSUE-299 nothing ran it, and the `verification_commands`
field that looked executable pointed at structural suites which pass whether
or not the postcondition holds.

This module closes that gap. A postcondition gains an optional `verify` spec:

    postconditions:
      - id: reports-or-writes
        check: writes .sweetclaude/disabled
        verify:
          kind: path_written
          block: "touch .sweetclaude/disabled"
          paths: [".sweetclaude/disabled"]

`block` is a substring of the skill's own code, not an index. Selecting by
content means an edit that removes the code fails the check loudly rather
than silently running whichever block moved into that position — the drift
failure mode ISSUE-249 was, and the reason
tests/test_fresh_project_onboarding.py extracts init's block instead of
copying it.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "config" / "capability-manifest.yaml"
SKILLS_DIR = REPO_ROOT / "skills"
SKILL_LIBRARY_DIR = REPO_ROOT / "skill-library"

FENCE = re.compile(r"```(?:bash|sh|python|python3)\n(.*?)```", re.S)


class PostconditionError(Exception):
    """Base for every way a postcondition check can fail to conclude."""


class BlockNotFound(PostconditionError):
    """The skill no longer contains the code the postcondition names."""


class PostconditionFailed(PostconditionError):
    """The block ran and the declared postcondition did not hold."""


class UnsafeFixture(PostconditionError):
    """The target project is not an isolated fixture.

    purge's block is `rm -rf .sweetclaude/` and feature-setup's syncs into
    ~/.claude. Running either against the working repository would destroy
    real state, so the fixture path is checked before any block executes
    rather than trusting every future spec author to pass a temp dir.
    """


class VerifySpecMissing(PostconditionError):
    """The capability declares a postcondition with no executable check."""


class BlockDidNotRun(PostconditionError):
    """The block could not execute, so the check concluded nothing.

    Distinct from PostconditionFailed on purpose. A block that errors out
    before doing anything would satisfy a "nothing was written" assertion
    while proving nothing at all, and counting that as a pass is the exact
    shape of defect ISSUE-299 exists to close. ISSUE-299 requires such blocks
    to be listed with a reason and left at tier-1 rather than quietly
    counted, so this raises instead of returning green.
    """


@dataclass
class VerifyResult:
    capability: str
    postcondition_id: str
    passed: bool
    detail: str = ""
    stdout: str = ""
    stderr: str = ""
    paths_checked: list[str] = field(default_factory=list)
    blocks_run: int = 0
    evidence: str = "unaided"


def load_manifest(path: Path | None = None) -> dict:
    return yaml.safe_load((path or MANIFEST).read_text(encoding="utf-8"))


def _skill_dir_name(capability: dict) -> str:
    """The manifest names the delegate as `sweetclaude:<skill>`."""
    delegate = capability.get("delegate_skill") or ""
    return delegate.split(":", 1)[-1]


def resolve_skill_markdown(skill: str, skills_dir: Path | None = None) -> Path:
    """Resolve a workflow from its Tier 1 or Tier 2 location.

    Capability records retain the focused workflow name because that is the
    executable unit whose postcondition is being checked. Public slash
    commands are now categories, however, and focused workflows live below
    ``skill-library/<category>/``. Test callers may pass a temporary
    ``skills_dir`` containing a single workflow; in that case do not search
    the repository library and accidentally validate the real file.
    """
    if skills_dir is not None:
        return skills_dir / skill / "SKILL.md"

    tier_one = SKILLS_DIR / skill / "SKILL.md"
    if tier_one.is_file():
        return tier_one

    matches = sorted(SKILL_LIBRARY_DIR.glob(f"*/{skill}/SKILL.md"))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        return tier_one
    raise PostconditionError(
        f"workflow {skill!r} is ambiguous in the Tier 2 library: "
        f"{', '.join(str(p.relative_to(REPO_ROOT)) for p in matches)}"
    )


def extract_blocks(skill_md: Path) -> list[str]:
    text = skill_md.read_text(encoding="utf-8")
    return [b for b in FENCE.findall(text) if b.strip()]


def select_block(blocks: list[str], selector: str, *, skill: str) -> str:
    """Pick the block containing `selector`.

    Ambiguity is an error too: if a selector matches more than one block the
    check would silently depend on ordering, which is the property this
    function exists to remove.
    """
    hits = [b for b in blocks if selector in b]
    if not hits:
        raise BlockNotFound(
            f"skills/{skill}/SKILL.md has no code block containing "
            f"{selector!r} — the skill changed, or the manifest's verify "
            f"spec is stale. Nothing was run."
        )
    if len(hits) > 1:
        raise BlockNotFound(
            f"selector {selector!r} matches {len(hits)} blocks in "
            f"skills/{skill}/SKILL.md — make it unambiguous so the check "
            f"does not depend on block order."
        )
    return hits[0]


def block_env() -> dict[str, str]:
    """Skills reference ${CLAUDE_PLUGIN_ROOT}; unset it and every such block
    resolves to /scripts/... and fails for the wrong reason."""
    import os

    return dict(
        os.environ,
        CLAUDE_PLUGIN_ROOT=str(REPO_ROOT),
        CLAUDE_SKILL_DIR=str(REPO_ROOT / "skills"),
    )


def apply_substitutions(code: str, subs: dict[str, str]) -> str:
    """Fill in the values a model would supply before running a block.

    Skills are model-executed templates. A block may carry `<title>` for the
    model to replace, or `$GLOSSARY` inside a *quoted* heredoc where the shell
    will never expand it — product-terminology's block reaches Python as the
    literal string "$GLOSSARY", so os.path.dirname returns "" and the write
    fails for a reason that has nothing to do with the postcondition.

    Substituting makes such a block runnable, but it weakens the evidence: the
    block's logic is still the skill's, while the value is the harness's. Specs
    using this must declare `evidence: substituted` so the two are never
    counted as equal, and an undeclared substitution is refused below.
    """
    missing = [k for k in subs if k not in code]
    if missing:
        raise BlockNotFound(
            f"substitution keys not present in the selected block: {missing}. "
            f"A stale substitution silently does nothing, so it is an error."
        )
    for key, value in subs.items():
        code = code.replace(key, str(value))
    return code


def run_block(code: str, project: Path, *, timeout: int = 30) -> subprocess.CompletedProcess:
    project.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        ["bash", "-c", code],
        cwd=str(project),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=block_env(),
    )


# --- check kinds ---------------------------------------------------------

def _check_path_written(spec: dict, project: Path, proc, result: VerifyResult) -> None:
    missing = []
    for rel in spec.get("paths", []):
        result.paths_checked.append(rel)
        if not (project / rel).exists():
            missing.append(rel)
    if missing:
        raise PostconditionFailed(
            f"{result.capability}: the block ran (exit {proc.returncode}) but "
            f"did not write {', '.join(missing)}. "
            f"stderr={proc.stderr.strip()[:300]!r}"
        )


def snapshot_tree(root: Path, *, ignore: tuple[str, ...] = (".git",)) -> dict[str, str]:
    """Content hash of every file under root, for before/after comparison.

    Hashing content rather than stat means a rewrite with identical bytes is
    correctly not a mutation, and a same-size edit correctly is.
    """
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if any(part in ignore for part in p.parts):
            continue
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def diff_trees(before: dict[str, str], after: dict[str, str]) -> dict[str, list[str]]:
    return {
        "added": sorted(set(after) - set(before)),
        "removed": sorted(set(before) - set(after)),
        "modified": sorted(k for k in set(before) & set(after) if before[k] != after[k]),
    }


def _check_path_absent(spec: dict, project: Path, proc, result: VerifyResult) -> None:
    present = []
    for rel in spec.get("paths", []):
        result.paths_checked.append(rel)
        if (project / rel).exists():
            present.append(rel)
    if present:
        raise PostconditionFailed(
            f"{result.capability}: the block ran (exit {proc.returncode}) but "
            f"{', '.join(present)} still exists."
        )


def _check_artifact_written(spec: dict, project: Path, proc, result: VerifyResult) -> None:
    """The 23 identical `artifact exists at the configured base_path` checks.

    The base path is resolved from the project's own artifact-privacy.yaml
    rather than hardcoded, because that indirection is the thing under test:
    a skill writing to a path nothing reads was ISSUE-250.
    """
    category = spec.get("category", "product")
    privacy = project / ".sweetclaude" / "artifact-privacy.yaml"
    if not privacy.is_file():
        raise BlockDidNotRun(
            f"{result.capability}: the fixture has no .sweetclaude/artifact-privacy.yaml, "
            f"so 'the configured base_path' cannot be resolved and the check "
            f"would assert against a guess."
        )
    conf = yaml.safe_load(privacy.read_text(encoding="utf-8")) or {}
    base = ((conf.get("categories") or {}).get(category) or {}).get("base_path")
    if not base:
        raise BlockDidNotRun(
            f"{result.capability}: artifact-privacy.yaml declares no base_path "
            f"for category {category!r}."
        )
    base_dir = project / base.rstrip("/")
    result.paths_checked.append(str(base_dir.relative_to(project)))
    pattern = spec.get("artifact_glob", "**/*")
    found = [p for p in base_dir.glob(pattern) if p.is_file()] if base_dir.is_dir() else []
    if not found:
        raise PostconditionFailed(
            f"{result.capability}: the block ran (exit {proc.returncode}) but wrote no "
            f"artifact under the configured base_path {base}. "
            f"stderr={proc.stderr.strip()[:300]!r}"
        )


def _check_content_changed(spec: dict, project: Path, proc, result: VerifyResult) -> None:
    """The block must change a file that already exists.

    `path_written` is the wrong check for a pre-existing file: asserting that
    .sweetclaude/state/sweetclaude.yaml exists after a block runs passes
    whether or not the block did anything, which is a check that cannot fail.
    """
    before = spec.get("_before") or {}
    changed = []
    for rel in spec.get("paths", []):
        result.paths_checked.append(rel)
        f = project / rel
        after = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
        if before.get(rel) != after:
            changed.append(rel)
    if not changed:
        raise PostconditionFailed(
            f"{result.capability}: the block ran (exit {proc.returncode}) but left "
            f"{', '.join(spec.get('paths', [])) or 'the target'} byte-identical. "
            f"stderr={proc.stderr.strip()[:300]!r}"
        )


def _check_state_key_written(spec: dict, project: Path, proc, result: VerifyResult) -> None:
    """A named key must appear in a YAML file, optionally with a given value.

    Precise enough to fail: unlike a file-existence check, the key is absent
    from the fixture until the block puts it there.
    """
    rel = spec["file"]
    result.paths_checked.append(rel)
    f = project / rel
    if not f.is_file():
        raise PostconditionFailed(
            f"{result.capability}: {rel} does not exist after the block ran."
        )
    text = f.read_text(encoding="utf-8")
    # Work items are markdown with YAML frontmatter, not pure YAML. Loading the
    # whole file would fail on the body and report a missing key for the wrong
    # reason.
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end == -1:
            raise PostconditionFailed(
                f"{result.capability}: {rel} opens a frontmatter block that never closes.")
        text = text[4:end]
    node = yaml.safe_load(text) or {}
    trail = []
    for key in spec["key_path"]:
        trail.append(str(key))
        if not isinstance(node, dict) or key not in node:
            raise PostconditionFailed(
                f"{result.capability}: the block ran (exit {proc.returncode}) but "
                f"{'.'.join(trail)} is absent from {rel}. "
                f"stderr={proc.stderr.strip()[:300]!r}"
            )
        node = node[key]
    if "value" in spec and node != spec["value"]:
        raise PostconditionFailed(
            f"{result.capability}: {'.'.join(trail)} is {node!r}, "
            f"expected {spec['value']!r}."
        )


CHECKS = {
    "path_written": _check_path_written,
    "path_absent": _check_path_absent,
    "artifact_written": _check_artifact_written,
    "content_changed": _check_content_changed,
    "state_key_written": _check_state_key_written,
}


# An `ignore` entry may never cover a source-of-truth artifact. Without this,
# the mechanism that excuses a derived cache becomes a blanket way to make any
# no_mutation check pass, which is worse than not having the check.
PROTECTED_PREFIXES = (
    ".sweetclaude/state",
    ".sweetclaude/product",
    ".sweetclaude/strategy",
    ".sweetclaude/technical",
    ".sweetclaude/design",
    ".sweetclaude/work",
)


def validate_ignore(ignore: list[str], capability_id: str) -> list[str]:
    """Reject an ignore list that could hide a real mutation."""
    cleaned = []
    for raw in ignore:
        entry = str(raw).strip()
        if entry in ("", ".", "/", "./", "*", "**"):
            raise PostconditionError(
                f"{capability_id}: ignore entry {raw!r} would exclude the whole "
                f"project, which defeats the check."
            )
        # lstrip("./") would strip the leading dot as a character, turning
        # ".sweetclaude/cache" into "sweetclaude/cache" and defeating every
        # comparison below. Remove a "./" prefix only.
        norm = entry[2:] if entry.startswith("./") else entry
        norm = norm.rstrip("/") + "/"
        for protected in PROTECTED_PREFIXES:
            if norm.startswith(protected.rstrip("/")):
                raise PostconditionError(
                    f"{capability_id}: ignore entry {raw!r} covers {protected}, a "
                    f"source-of-truth path. Only derived artifacts may be ignored."
                )
        cleaned.append(norm)
    return cleaned


def apply_seed(seed: dict, project: Path) -> list[str]:
    """Write the work-item files a check needs before the block runs.

    A write-back check needs something to write back to. Declaring the seed in
    the spec keeps it visible, and keeps it out of the shared fixture where it
    would make other capabilities' checks pass for free — a seeded MS-001 in
    the fixture would satisfy project.goals' artifact_written glob without its
    block doing anything.

    The spec gives frontmatter as a mapping rather than raw file text. An
    embedded markdown block scalar has to be indented deeper than its key, and
    getting that wrong makes the whole manifest unparseable — which is exactly
    what it did on the first attempt.
    """
    written = []
    for rel, fields in seed.items():
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        front = yaml.safe_dump(fields, default_flow_style=False, sort_keys=False)
        target.write_text(f"---\n{front}---\n\nseeded by the postcondition harness\n",
                          encoding="utf-8")
        written.append(rel)
    return written


def _verify_no_mutation(
    capability_id: str,
    entry: dict,
    postcondition: dict,
    spec: dict,
    project: Path,
    skill_md: Path,
    skill: str,
) -> VerifyResult:
    """`no project files are modified`, asserted across the whole skill.

    Checking one hand-picked block would measure the wrong thing: a skill can
    hold a reporting block and a writing block side by side, and verifying the
    read-only claim against only the read-only block is how the claim stayed
    wrong. So the default is every block in the skill.

    A block that exits nonzero is not evidence of anything — it did not write
    because it did not run. Those are collected and raised as BlockDidNotRun
    rather than being allowed to satisfy the assertion by absence.
    """
    if "blocks" not in spec:
        raise PostconditionError(
            f"{capability_id}: no_mutation requires an explicit `blocks` key. "
            f"Skill code blocks are gated by the prose around them, not run in "
            f"sequence, so defaulting to every block measures a path the skill "
            f"never takes — `session.help` writes its welcome-skip flag only "
            f"when the user asks, and running that block unprompted made its "
            f"postcondition look false. Declare `all` only when every block in "
            f"the skill is genuinely on the non-mutating path."
        )
    blocks = extract_blocks(skill_md)
    which = spec["blocks"]
    if which != "all":
        blocks = [select_block(blocks, sel, skill=skill) for sel in which]

    result = VerifyResult(
        capability=capability_id,
        postcondition_id=postcondition["id"],
        passed=False,
    )
    if spec.get("seed_frontmatter"):
        apply_seed(spec["seed_frontmatter"], project)

    ignore = validate_ignore(spec.get("ignore") or [], capability_id)

    def _filtered(tree: dict[str, str]) -> dict[str, str]:
        return {k: v for k, v in tree.items()
                if not any(k.startswith(pref) for pref in ignore)}

    before = _filtered(snapshot_tree(project))
    failed_to_run: list[str] = []
    for code in blocks:
        proc = run_block(code, project)
        if proc.returncode != 0:
            failed_to_run.append(
                f"exit {proc.returncode}: {code.strip().splitlines()[0][:70]!r} "
                f"({proc.stderr.strip()[:120]})"
            )
        else:
            result.blocks_run += 1
    after = _filtered(snapshot_tree(project))

    delta = diff_trees(before, after)
    if any(delta.values()):
        raise PostconditionFailed(
            f"{capability_id} declares {postcondition['check']!r} but running its "
            f"own blocks changed the project: "
            f"added={delta['added']} removed={delta['removed']} "
            f"modified={delta['modified']}"
        )

    if failed_to_run:
        raise BlockDidNotRun(
            f"{capability_id}: no mutation was observed, but "
            f"{len(failed_to_run)} of {len(blocks)} blocks did not execute, so "
            f"the check concluded nothing about them. Stays tier-1. "
            + " | ".join(failed_to_run)
        )

    result.passed = True
    result.detail = f"{postcondition['id']}: {postcondition['check']}"
    return result


def verify_capability(
    capability_id: str,
    project: Path,
    *,
    skills_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> VerifyResult:
    """Run the capability's block and assert its declared postcondition.

    Raises rather than returning a failed result: a check that can be ignored
    by not reading the return value is the same failure this closes.
    """
    project = Path(project).resolve()
    if project == REPO_ROOT or REPO_ROOT in project.parents:
        raise UnsafeFixture(
            f"refusing to run capability blocks against {project} — it is inside "
            f"the working repository at {REPO_ROOT}. Pass an isolated temp "
            f"directory: some blocks delete .sweetclaude/ outright."
        )

    manifest = load_manifest(manifest_path)
    entry = manifest["capabilities"].get(capability_id)
    if entry is None:
        raise PostconditionError(f"no such capability: {capability_id}")

    specced = [p for p in entry.get("postconditions", []) if p.get("verify")]
    if not specced:
        raise VerifySpecMissing(
            f"{capability_id} declares a postcondition with no `verify` spec — "
            f"it is prose, and prose is not verification."
        )
    postcondition = specced[0]
    spec = postcondition["verify"]

    kind = spec.get("kind")
    NON_BLOCK_KINDS = {"no_mutation"}
    if kind not in CHECKS and kind not in NON_BLOCK_KINDS:
        raise PostconditionError(
            f"{capability_id}: unknown verify kind {kind!r}. "
            f"known kinds: {', '.join(sorted(set(CHECKS) | NON_BLOCK_KINDS))}"
        )

    skill = _skill_dir_name(entry)
    skill_md = resolve_skill_markdown(skill, skills_dir)
    if not skill_md.is_file():
        raise BlockNotFound(f"{skill_md} does not exist")

    if kind == "no_mutation":
        return _verify_no_mutation(
            capability_id, entry, postcondition, spec, project, skill_md, skill
        )

    code = select_block(extract_blocks(skill_md), spec["block"], skill=skill)
    if spec.get("seed_frontmatter"):
        apply_seed(spec["seed_frontmatter"], project)
    subs = spec.get("substitutions") or {}
    if subs:
        if spec.get("evidence") != "substituted":
            raise PostconditionError(
                f"{capability_id}: a verify spec with `substitutions` must also "
                f"declare `evidence: substituted`, so harness-supplied values are "
                f"never reported as evidence equal to a block that ran unaided."
            )
        code = apply_substitutions(code, subs)
    if kind == "content_changed":
        spec = dict(spec)
        spec["_before"] = {
            rel: (
                hashlib.sha256((project / rel).read_bytes()).hexdigest()
                if (project / rel).is_file() else None
            )
            for rel in spec.get("paths", [])
        }
    proc = run_block(code, project)

    result = VerifyResult(
        capability=capability_id,
        postcondition_id=postcondition["id"],
        passed=False,
        stdout=proc.stdout,
        stderr=proc.stderr,
        evidence=spec.get("evidence", "unaided"),
    )
    result.blocks_run = 1
    CHECKS[kind](spec, project, proc, result)
    result.passed = True
    result.detail = f"{postcondition['id']}: {postcondition['check']}"
    return result
