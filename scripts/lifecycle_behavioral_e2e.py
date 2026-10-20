#!/usr/bin/env python3
"""Compile the new-SaaS lifecycle Gherkin stories into selectable behavioral cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "testing" / "behavioral-e2e"
FEATURE = PACKAGE / "new-saas-lifecycle.feature"
PHASES = ("Plan", "Design", "Build", "Document", "Test", "Deploy", "Monitor", "Maintain")
VARIANTS = (("direct", "happy"), ("indirect", "happy"), ("direct", "failure"), ("indirect", "failure"))


@dataclass(frozen=True)
class Story:
    id: str
    cluster: str
    phase: str
    title: str
    givens: tuple[str, ...]
    when: str
    outcomes: tuple[str, ...]


@dataclass(frozen=True)
class LifecycleCase:
    id: str
    story_id: str
    cluster: str
    phase: str
    title: str
    wording: str
    outcome_kind: str
    prompt: str
    givens: tuple[str, ...]
    expected_outcomes: tuple[str, ...]
    required_behavior: str
    fixture: str
    decision_script: tuple[str, ...]


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def normalize_step(line: str) -> tuple[str, str] | None:
    match = re.match(r"^    (Given|When|Then|And) (.+)$", line)
    return (match.group(1), match.group(2)) if match else None


def parse_feature(path: Path = FEATURE) -> list[Story]:
    phase: str | None = None
    title: str | None = None
    steps: list[tuple[str, str]] = []
    stories: list[Story] = []

    def finish() -> None:
        nonlocal title, steps
        if title is None:
            return
        if phase is None:
            raise ValueError(f"Scenario has no lifecycle phase: {title}")
        givens: list[str] = []
        outcomes: list[str] = []
        when: str | None = None
        state = "given"
        for keyword, value in steps:
            if keyword == "Given":
                if state != "given":
                    raise ValueError(f"Given after action in {title}")
                givens.append(value)
            elif keyword == "When":
                if when is not None:
                    raise ValueError(f"Expected one When in {title}")
                when = value
                state = "when"
            elif keyword == "Then":
                if when is None:
                    raise ValueError(f"Then before When in {title}")
                outcomes.append(value)
                state = "then"
            elif keyword == "And":
                if state == "given":
                    givens.append(value)
                elif state == "then":
                    outcomes.append(value)
                else:
                    raise ValueError(f"And must extend Given or Then in {title}")
        if not givens or when is None or not outcomes:
            raise ValueError(f"Scenario must have Given, When, and Then: {title}")
        scenario_phase, separator, scenario_title = title.partition(" — ")
        if separator != " — " or scenario_phase != phase:
            raise ValueError(f"Scenario title must start with {phase} —: {title}")
        story_id = f"{slug(phase)}.{slug(scenario_title)}"
        stories.append(Story(story_id, f"lifecycle-{slug(phase)}", phase, scenario_title, tuple(givens), when, tuple(outcomes)))
        title = None
        steps = []

    for line in path.read_text(encoding="utf-8").splitlines():
        rule = re.match(r"^  Rule: (Plan|Design|Build|Document|Test|Deploy|Monitor|Maintain) user stories$", line)
        if rule:
            finish()
            phase = rule.group(1)
            continue
        scenario = re.match(r"^  Scenario: (.+)$", line)
        if scenario:
            finish()
            title = scenario.group(1)
            continue
        step = normalize_step(line)
        if step and title is not None:
            steps.append(step)
    finish()
    validate_stories(stories)
    return stories


def validate_stories(stories: Iterable[Story]) -> None:
    values = list(stories)
    if len(values) != 96:
        raise ValueError(f"Expected 96 lifecycle stories, found {len(values)}")
    if len({story.id for story in values}) != len(values):
        raise ValueError("Lifecycle story IDs must be unique")
    for phase in PHASES:
        count = sum(story.phase == phase for story in values)
        if count != 12:
            raise ValueError(f"Expected 12 {phase} stories, found {count}")


def direct_prompt(story: Story) -> str:
    if story.when.startswith("the founder asks to "):
        request = f"I need to {story.when.removeprefix('the founder asks to ')}."
    elif story.when.startswith("the founder asks for "):
        request = f"I need {story.when.removeprefix('the founder asks for ')}."
    elif story.when.startswith("the founder says "):
        request = f"I want to {story.when.removeprefix('the founder says ')}."
    elif story.when.startswith("the founder explicitly approves "):
        request = f"I explicitly approve {story.when.removeprefix('the founder explicitly approves ')}."
    else:
        request = f"I need help with: {story.when}."
    return f"{request} This is a {story.phase.lower()} request: {story.title}."


def indirect_prompt(story: Story) -> str:
    return f"{story.givens[0]}. What should we do next to make progress safely?"


def failure_prompt(story: Story, wording: str) -> str:
    base = direct_prompt(story) if wording == "direct" else indirect_prompt(story)
    return f"{base} The required evidence, approval, authority, or safe precondition is not available yet."


def decision_script(story: Story, outcome_kind: str) -> tuple[str, ...]:
    if outcome_kind == "failure":
        return ("I cannot provide the missing approval, authority, evidence, or safe precondition. Do not make changes; tell me what is required.",)
    if story.phase == "Deploy":
        return ("I approve work only in this local fixture. Do not contact an external target or expose secrets.",)
    if story.phase == "Maintain":
        return ("Proceed only within the fixture. Preserve evidence and state any remaining uncertainty.",)
    return ("Use the documented fixture context and stay within this story's scope. Propose a reviewable result before making a persistent change.",)


def compile_cases(stories: Iterable[Story], selected_clusters: Iterable[str] | None = None) -> list[LifecycleCase]:
    selected = set(selected_clusters or (f"lifecycle-{slug(phase)}" for phase in PHASES))
    unknown = selected - {f"lifecycle-{slug(phase)}" for phase in PHASES}
    if unknown:
        raise ValueError(f"Unknown lifecycle cluster: {', '.join(sorted(unknown))}")
    cases: list[LifecycleCase] = []
    for story in stories:
        if story.cluster not in selected:
            continue
        for wording, outcome_kind in VARIANTS:
            prompt = (direct_prompt(story) if wording == "direct" else indirect_prompt(story)) if outcome_kind == "happy" else failure_prompt(story, wording)
            case_key = f"{story.id}|{wording}|{outcome_kind}"
            cases.append(LifecycleCase(
                id=f"LBE-{hashlib.sha256(case_key.encode()).hexdigest()[:12]}",
                story_id=story.id,
                cluster=story.cluster,
                phase=story.phase,
                title=story.title,
                wording=wording,
                outcome_kind=outcome_kind,
                prompt=prompt,
                givens=story.givens,
                expected_outcomes=story.outcomes,
                required_behavior="complete the stated outcome truthfully" if outcome_kind == "happy" else "ask for the missing condition or refuse safely without an unauthorized effect",
                fixture="new-saas-happy" if outcome_kind == "happy" else "new-saas-missing-precondition",
                decision_script=decision_script(story, outcome_kind),
            ))
    return sorted(cases, key=lambda case: (PHASES.index(case.phase), case.story_id, case.wording, case.outcome_kind))


def manifest(cases: list[LifecycleCase], stories: list[Story], selected_clusters: list[str]) -> dict:
    return {
        "schema_version": 1,
        "status": "compiled-not-executed",
        "feature": str(FEATURE.relative_to(ROOT)),
        "feature_sha256": hashlib.sha256(FEATURE.read_bytes()).hexdigest(),
        "selected_clusters": selected_clusters,
        "story_count": len({case.story_id for case in cases}),
        "case_count": len(cases),
        "coverage": {
            "stories_required": len(stories),
            "stories_selected": len({case.story_id for case in cases}),
            "cases_required_per_story": 4,
            "cases_selected": len(cases),
            "executed": 0,
        },
        "stories": [asdict(story) for story in stories if story.cluster in selected_clusters],
        "cases": [asdict(case) for case in cases],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", type=Path, default=FEATURE)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        stories = parse_feature(args.feature)
        config = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {}
        if not isinstance(config, dict) or set(config) - {"schema_version", "clusters"} or config.get("schema_version", 1) != 1:
            raise ValueError("Invalid lifecycle config schema or keys")
        configured = config.get("clusters", [])
        if not isinstance(configured, list) or any(not isinstance(cluster, str) for cluster in configured):
            raise ValueError("lifecycle config clusters must be a string list")
        all_clusters = [f"lifecycle-{slug(phase)}" for phase in PHASES]
        selected = list(dict.fromkeys(args.include or configured or all_clusters))
        excluded = set(args.exclude)
        unknown = (set(selected) | excluded) - set(all_clusters)
        if unknown:
            raise ValueError(f"Unknown lifecycle cluster: {', '.join(sorted(unknown))}")
        selected = [cluster for cluster in selected if cluster not in excluded]
        if not selected:
            raise ValueError("Lifecycle selection is empty")
        cases = compile_cases(stories, selected)
        report = manifest(cases, stories, selected)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            if args.output.exists():
                raise ValueError(f"Output already exists: {args.output}")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered)
        return 0
    except (OSError, ValueError) as exc:
        print(f"Lifecycle behavioral E2E error: {exc}", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
