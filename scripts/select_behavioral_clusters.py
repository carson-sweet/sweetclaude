#!/usr/bin/env python3
"""Preview a selection from the documented behavioral inventory; never execute tests."""

from __future__ import annotations

import argparse
from collections import Counter
import fnmatch
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "testing" / "behavioral-e2e"
FACETS = ("subject", "layer", "kind", "wording", "entry", "profile")
PUBLIC = {"go", "plan", "design", "build", "maintain", "configure", "utils", "status", "help"}


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def expand(patterns: list[str], catalog: dict) -> list[str]:
    matched = set()
    names = catalog["clusters"]
    aliases = catalog["aliases"]
    for pattern in patterns:
        canonical = aliases.get(pattern, pattern)
        hits = {name for name in names if fnmatch.fnmatchcase(name, canonical)}
        if not hits:
            raise ValueError(f"Unknown cluster or unmatched pattern: {pattern}")
        matched.update(hits)
    return sorted(matched)


def lists_by_facet(names: list[str], catalog: dict) -> dict[str, set[str]]:
    result = {facet: set() for facet in FACETS}
    for name in names:
        cluster = catalog["clusters"][name]
        result[cluster["facet"]].update(cluster["members"])
    return result


def resolve_selection(catalog: dict, preset: str | None, enabled: list[str], disabled: list[str]) -> tuple[dict, list[str], list[str]]:
    if not preset and not enabled:
        raise ValueError("Choose --preset, --include, or an enabled cluster in --config; no implicit full run.")
    base = []
    if preset:
        if preset not in catalog["presets"]:
            raise ValueError(f"Unknown preset: {preset}")
        base = expand(catalog["presets"][preset]["enable"], catalog)
    positive = expand(enabled, catalog)
    negative = expand(disabled, catalog)
    base_facets = lists_by_facet(base, catalog)
    positive_facets = lists_by_facet(positive, catalog)
    negative_facets = lists_by_facet(negative, catalog)
    chosen = {}
    for facet in FACETS:
        values = positive_facets[facet] or base_facets[facet] or set(catalog["defaults"][facet])
        chosen[facet] = sorted(values - negative_facets[facet])
        if not chosen[facet]:
            raise ValueError(f"Selection is empty in facet {facet!r}; exclusions take precedence.")
    effective = sorted({name for name in base if not positive_facets[catalog["clusters"][name]["facet"]]} | set(positive))
    return chosen, effective, negative


def operation_filter(patterns: list[str], operations: list[dict]) -> set[str]:
    result = set()
    for pattern in patterns:
        hits = {op["id"] for op in operations if fnmatch.fnmatchcase(op["id"], pattern)}
        if not hits:
            raise ValueError(f"Unknown operation or unmatched pattern: {pattern}")
        result.update(hits)
    return result


def variants(key: str, workflow: dict) -> list[dict]:
    if workflow["internal_or_redirect"]:
        entries = ["caller"]
    elif key.startswith("top/"):
        entries = ["command", "bare", "literal"]
    else:
        entries = ["category", "go", "bare"]
    result = []
    for entry in entries:
        for wording in (["literal"] if entry == "literal" else ["direct", "indirect"]):
            result.append({"entry": entry, "wording": wording, "id": "literal-no-args" if entry == "literal" else f"{entry}-{wording}"})
    return result


def plan_selection(inventory: dict, catalog: dict, chosen: dict, included: list[str], excluded: list[str], only_ops: list[str], omit_ops: list[str]) -> dict:
    selected = set(chosen["subject"])
    allowed_ops = operation_filter(only_ops, inventory["operations"]) if only_ops else None
    excluded_ops = operation_filter(omit_ops, inventory["operations"])
    operation_plans = []
    auxiliary_plans = []
    omitted = []
    selected_workflows = set()
    for subject_id in sorted(selected):
        subject = catalog["subjects"][subject_id]
        layers = sorted(set(subject["layers"]) & set(chosen["layer"]))
        if not layers:
            omitted.append({"subject": subject_id, "reason": "no applicable selected layer"})
            continue
        if subject["type"] != "workflow":
            if only_ops:
                omitted.append({"subject": subject_id, "reason": "explicit operation filter only admits workflow operations"})
                continue
            entries = sorted(set(subject["entries"]) & set(chosen["entry"]))
            wording = [x for x in chosen["wording"] if x != "literal"]
            if not entries or not wording:
                omitted.append({"subject": subject_id, "reason": "no applicable selected entry/wording combination"})
                continue
            auxiliary_plans.append({"subject": subject_id, "type": subject["type"], "reference": subject["reference"], "layers": layers, "kinds": chosen["kind"], "entries_to_expand": entries, "wording_to_expand": wording, "profiles_to_resolve": chosen["profile"], "status": "planned-unexpanded"})
            continue
        key = subject["reference"]
        workflow = inventory["workflows"][key]
        applicable_variants = [v for v in variants(key, workflow) if v["entry"] in chosen["entry"] and v["wording"] in chosen["wording"]]
        admitted = 0
        literal_added = False
        for op in workflow["operations"]:
            if (allowed_ops is not None and op["id"] not in allowed_ops) or op["id"] in excluded_ops:
                continue
            entry_variants = [v for v in applicable_variants if v["entry"] != "literal"]
            if not literal_added and not only_ops:
                entry_variants += [v for v in applicable_variants if v["entry"] == "literal"]
                literal_added = True
            if not entry_variants:
                continue
            operation_plans.append({"operation_id": op["id"], "workflow": key, "source": workflow["source"], "layers": layers, "variants": entry_variants, "kinds": chosen["kind"], "profiles_to_resolve": chosen["profile"], "branch_obligations": workflow["branches"], "execution_boundary": "public-entry-owned behavior; stop at library handoff" if key.startswith("top/") and key.split("/")[1] in PUBLIC else "selected workflow and legitimate dependencies", "routing_boundary": "observe required dispatch, index and workflow-body reads; stop before operation execution", "status": "planned-unexpanded"})
            admitted += 1
        if admitted:
            selected_workflows.add(key)
        else:
            omitted.append({"subject": subject_id, "reason": "no matching operation or entry/wording combination"})
    if not operation_plans and not auxiliary_plans:
        raise ValueError("Selection produces no applicable operation or auxiliary plans.")
    edges = [e["id"] for e in inventory["skill_edges"] if e["owner"] in selected_workflows]
    sources = {inventory["workflows"][k]["source"] for k in selected_workflows}
    for e in inventory["helper_edges"]:
        if e["owner"] in selected_workflows:
            sources.add(e["target"])
    for item in auxiliary_plans:
        subject = catalog["subjects"][item["subject"]]
        sources.update(subject.get("sources", []))
    anchors = [d["id"] for d in inventory["source_decisions"] if d["owner"] in selected_workflows or d["source"] in sources]
    selected_types = Counter(catalog["subjects"][x["subject"]]["type"] for x in auxiliary_plans)
    return {
        "schema_version": 1,
        "status": "selection-preview-no-tests-executed",
        "inventory_sha256": catalog["inventory_sha256"],
        "enabled_clusters": included,
        "disabled_clusters": excluded,
        "resolved_facets": chosen,
        "operation_patterns": {"include": only_ops, "exclude": omit_ops},
        "summary": {"workflows": len(selected_workflows), "base_operations": len(operation_plans), "auxiliary_subjects": len(auxiliary_plans), "auxiliary_by_type": dict(sorted(selected_types.items())), "effective_layers": sorted({layer for item in operation_plans + auxiliary_plans for layer in item["layers"]}), "source_anchors_to_map": len(anchors), "routing_edges_to_map": len(edges), "omitted_inapplicable_subjects": len(omitted)},
        "operation_plans": operation_plans,
        "auxiliary_plans": auxiliary_plans,
        "omitted_subjects": omitted,
        "source_anchor_ids": anchors,
        "routing_edge_ids": edges,
        "coverage_limits": ["Branches, profile applicability and concrete fixtures still require scenario expansion.", "Auxiliary entry prompts and branch variants still require scenario expansion.", "Shared or transitive source obligations require explicit ownership mapping; selected anchors are a starting set.", "Selected counts are planned scope, not executed or passing tests.", "Excluded standalone tests do not authorize bypassing runtime dependencies or guards."],
        "non_optional_invariants": catalog["non_optional_invariants"],
    }


def strings(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise ValueError(f"{name} must be a list of cluster-name strings")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=PACKAGE / "clusters.json")
    parser.add_argument("--inventory", type=Path, default=PACKAGE / "inventory.json")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--preset")
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--operation", action="append", default=[])
    parser.add_argument("--exclude-operation", action="append", default=[])
    parser.add_argument("--list-clusters", nargs="?", const="*")
    parser.add_argument("--list-presets", action="store_true")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        catalog = read_object(args.catalog)
        inventory = read_object(args.inventory)
        if catalog.get("schema_version") != 1:
            raise ValueError("Unsupported cluster catalog schema")
        if hashlib.sha256(args.inventory.read_bytes()).hexdigest() != catalog["inventory_sha256"]:
            raise ValueError("Catalog does not match this inventory snapshot; reconcile cluster membership first.")
        all_subjects = set(catalog["subjects"])
        for name, cluster in catalog["clusters"].items():
            facet = cluster["facet"]
            if facet not in FACETS or not set(cluster["members"]) <= set(catalog["defaults"][facet]):
                raise ValueError(f"Invalid cluster membership: {name}")
        if set(catalog["defaults"]["subject"]) != all_subjects:
            raise ValueError("Default subject universe disagrees with catalog subjects")
        if args.list_presets:
            data = catalog["presets"]
            text = "\n".join(f"{name}: {item['description']}" for name, item in sorted(data.items()))
        elif args.list_clusters is not None:
            names = expand([args.list_clusters], catalog)
            data = {name: catalog["clusters"][name] for name in names}
            text = "\n".join(f"{name} [{item['facet']}; {len(item['members'])} members] {item['description']}" for name, item in data.items())
        else:
            config = read_object(args.config) if args.config else {}
            unknown = set(config) - {"schema_version", "preset", "enable", "disable", "switches", "operation", "exclude_operation"}
            if unknown or config.get("schema_version", 1) != 1:
                raise ValueError(f"Invalid selection config schema or keys: {sorted(unknown)}")
            enabled = strings(config.get("enable", []), "enable") + args.include
            disabled = strings(config.get("disable", []), "disable") + args.exclude
            switches = config.get("switches", {})
            if not isinstance(switches, dict) or any(not isinstance(k, str) or not isinstance(v, bool) for k, v in switches.items()):
                raise ValueError("switches must map cluster-name strings to true/false")
            enabled += [k for k, v in switches.items() if v]
            disabled += [k for k, v in switches.items() if not v]
            preset = args.preset if args.preset is not None else config.get("preset")
            if preset is not None and not isinstance(preset, str):
                raise ValueError("preset must be a string or null")
            chosen, included, excluded = resolve_selection(catalog, preset, enabled, disabled)
            configured_operations = strings(config.get("operation", []), "operation")
            configured_exclusions = strings(config.get("exclude_operation", []), "exclude_operation")
            data = plan_selection(inventory, catalog, chosen, included, excluded, configured_operations + args.operation, configured_exclusions + args.exclude_operation)
            s = data["summary"]
            text = "\n".join([
                "Selection preview only; no tests or model calls executed.",
                "Enabled: " + ", ".join(included),
                "Disabled: " + (", ".join(excluded) or "none"),
                f"Selected: {s['workflows']} workflows; {s['base_operations']} base operations; {s['auxiliary_subjects']} auxiliary subjects.",
                "Layers: " + ", ".join(s["effective_layers"]),
                "Kinds: " + ", ".join(chosen["kind"]) + "; wording: " + ", ".join(chosen["wording"]),
                f"Source obligations to map: {s['source_anchors_to_map']} anchors; {s['routing_edges_to_map']} routing edges.",
                f"Omitted as inapplicable: {s['omitted_inapplicable_subjects']} subjects (details in JSON output).",
                "Branch/profile expansion remains pending; these are not executable test counts.",
            ])
        rendered = json.dumps(data, indent=2, ensure_ascii=False) if args.format == "json" else text
        if args.output:
            target = args.output.resolve()
            protected = {args.inventory.resolve(), args.catalog.resolve()}
            if args.config:
                protected.add(args.config.resolve())
            if target in protected:
                raise ValueError("Output must not overwrite inventory, catalog or selection configuration")
            if target.exists():
                raise ValueError(f"Output already exists; choose a fresh path: {target}")
            with target.open("x", encoding="utf-8") as stream:
                stream.write(rendered + "\n")
            print(f"Selection preview written to {target}")
        else:
            print(rendered)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Selection error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
