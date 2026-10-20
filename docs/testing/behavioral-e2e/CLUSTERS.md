# Selectable behavioral test clusters

Version: 1.1.0

Date: 2026-10-19

Status: implemented inventory selection, scenario compilation and opt-in Tier 1 routing execution.

The [full inventory](README.md) remains the coverage baseline. This catalog makes subsets selectable without copying or deleting inventory rows. [clusters.json](clusters.json) defines the memberships and presets; [selection.json](selection.json) is an editable switch configuration. The [selector](../../../scripts/select_behavioral_clusters.py) resolves them into a reviewable run plan. It never starts tests, Claude, a model, a browser, or a provider.

## Pick the chunk you want

Run these commands from the repository root. Every command below previews scope only.

```bash
python3 scripts/select_behavioral_clusters.py --preset first-tier-routing
python3 scripts/select_behavioral_clusters.py --preset first-tier
python3 scripts/select_behavioral_clusters.py --preset routing
python3 scripts/select_behavioral_clusters.py --include skill:doctor
python3 scripts/select_behavioral_clusters.py --include family:configure
```

The first command selects nine public commands and their routing contracts. The second also includes behavior owned by those public commands, such as Go's proposal/menu logic and Status's views, stopping at the library handoff. The third covers routing and workflow loading across all 129 public/internal workflow subjects. The last two select one skill or one entire family, including their happy/failure and direct/indirect obligations.

Combine independent dimensions to narrow further:

```bash
python3 scripts/select_behavioral_clusters.py --include family:build --include family:maintain --include layer:routing
python3 scripts/select_behavioral_clusters.py --include skill:code-review --include kind:failure --include wording:indirect --include entry:category
python3 scripts/select_behavioral_clusters.py --preset routing --include skill:doctor
python3 scripts/select_behavioral_clusters.py --include 'skill:utils/corpus-*' --include layer:behavior
python3 scripts/select_behavioral_clusters.py --include skill:project-issues --operation 'build.project-issues.*-github'
python3 scripts/select_behavioral_clusters.py --include family:build --exclude skill:john-wick --exclude skill:orchestrator
```

The operation filter selects exactly the documented operations matching the pattern. For example, `*-github` includes changing the tracker to GitHub and the GitHub-specific issue operations. It does not include local issue operations or separately requested GitHub import/sync workflows.

An explicit operation filter omits skill-level literal no-argument discovery. That check belongs to the skill as a whole and should be selected with the skill/tier/family cluster instead.

Discover names and inspect exact memberships:

```bash
python3 scripts/select_behavioral_clusters.py --list-presets
python3 scripts/select_behavioral_clusters.py --list-clusters 'family:*'
python3 scripts/select_behavioral_clusters.py --list-clusters 'skill:configure/*'
python3 scripts/select_behavioral_clusters.py --list-clusters 'topic:*'
python3 scripts/select_behavioral_clusters.py --list-clusters 'hook:*'
python3 scripts/select_behavioral_clusters.py --list-clusters skill:doctor --format json
```

All shell wildcard arguments must be quoted. Unknown names and patterns matching nothing are errors. A command without an explicit preset or enabled cluster is an error; it cannot accidentally select the entire suite.

## Turn clusters on and off

The checked-in example selects `first-tier-routing`. Edit [selection.json](selection.json) and preview it:

```bash
python3 scripts/select_behavioral_clusters.py --config docs/testing/behavioral-e2e/selection.json
```

For example, this configuration selects Build and Maintain behavior, disables the two named skill clusters, and includes only failure scenarios:

```json
{
  "schema_version": 1,
  "preset": null,
  "enable": [],
  "disable": [],
  "switches": {
    "family:build": true,
    "family:maintain": true,
    "layer:behavior": true,
    "kind:failure": true,
    "skill:john-wick": false,
    "skill:orchestrator": false
  }
}
```

`true` enables a cluster. `false` excludes its members. An absent key is neutral. The `enable` and `disable` arrays accept the same names/patterns as the switches; they are useful for generated configurations. Exclusion always wins when memberships overlap. If all subjects or any required dimension are removed, preview fails explicitly instead of producing an empty green run.

Selection is a union within a dimension and an intersection between dimensions. Build plus Maintain includes both families; adding `layer:routing` restricts that combined scope to routing. Enabling two individual skills includes both. Enabling `kind:failure` restricts the result to failures.

Explicit positive selectors replace a preset's choices in that same dimension. Thus `--preset routing --include skill:doctor` preserves routing-only depth and narrows the subject to Doctor. It does not add Doctor to every skill in the routing preset. Positives in one dimension do not replace choices in another. CLI inclusions combine with configuration inclusions; `--preset` overrides the configuration's preset, and explicit exclusions remain in force.

Defaults for dimensions without a preset or explicit positive are all subjects, all applicable layers, both happy/failure outcomes, all applicable entry/wording forms, and all sixteen expansion profiles. At least one positive selector or preset is still required.

## Cluster dimensions and boundaries

| Dimension | Names | Membership and effect |
|---|---|---|
| Public tier | `tier:1-public` or `tier:1` | The nine public command subjects: Go, Plan, Design, Build, Maintain, Configure, Utils, Status, Help. |
| Internal top level | `tier:1-internal` | Master, Bootstrap, `_route`, Find Skill, Library Load; nine documented operations. Caller-only access remains required. |
| All top level | `tier:1-all` | The fourteen public/internal top-level subjects. |
| Library tier | `tier:2` | All 115 library workflows, including internal helpers and redirects. |
| Family | `family:plan`, `family:design`, `family:build`, `family:maintain`, `family:configure`, `family:utils` | The public category wrapper plus every workflow in that category's index. Go/Status/Help and independent hook/capability/journey subjects are not added. |
| Individual skill | `skill:<category>/<name>` or `skill:top/<command>` | One workflow and all its documented operations. Unique short aliases such as `skill:doctor`, `skill:code-review`, and `skill:go` are supported. |
| Related skills | `topic:<name>` | Explicit cross-category groups, such as `corpus`, `recovery`, `controlled-stories`, `testing`, `github`, `issue-tracking`, `sprints`, `mockups`, `onboarding`, and `incidents`. Discover the complete group list and membership with `--list-clusters`. |
| Routing depth | `layer:routing` | Assert request interpretation, category/loader selection, actual body reads, redirects, ambiguity handling and stop behavior; stop before executing the selected operation. Hook subjects cover registration/matching at this depth. |
| Behavior depth | `layer:behavior` | Assert selected subject's own branch handling, decisions, actual effects and truthful result. A public Tier 1 subject ends at its library handoff; a Tier 2 subject exercises its workflow and legitimate dependencies. |
| Full journey | `layer:journey` and `journey:J01`…`journey:J15` | The prescribed multi-turn integration journeys. Select the subject as well as its applicable layer, or use the `journeys` preset. Selecting this layer alone does not mean every skill independently becomes a journey. |
| Outcomes | `kind:happy`, `kind:failure` | Happy or expected-failure expansion, or both. An expected-failure test passes only on the correct safe failure behavior. |
| Wording | `wording:direct`, `wording:indirect`, `wording:literal` | Direct or indirect plain language; literal is public no-argument discovery and appears once per selected skill, not once per operation. |
| Entry | `entry:category`, `entry:go`, `entry:bare`, `entry:command`, `entry:caller`, `entry:literal`, `entry:journey` | Restrict the entry surface. Inapplicable combinations are listed as omissions and never reported as passed. |
| Expansion profile | `profile:P01`…`profile:P16` | Restrict dedicated profile expansion. Short aliases include `profile:modes`, `profile:durability`, `profile:boundaries`, `profile:truth-evidence`. Profile applicability still needs scenario mapping. |
| Hook group | `scope:hooks`, `hook:PreToolUse`, `hook:Stop`, etc. | All 19 hooks or one event's hooks. An exact command is selectable, for example `hook:PreToolUse/test-guardian`. |
| Capability | `scope:capabilities`, `capability:<manifest-id>` | All 132 declared capability contracts or one. Their supported layer is behavior and their entry is their legitimate caller. |
| Entire inventory | `scope:all` or the `full` preset | All 295 subjects: 129 workflows, 19 hooks, 132 capabilities and 15 journeys. Scope subjects are coverage owners, not counts of executable tests. |

Family memberships are Plan 25, Design 16, Build 29, Maintain 7, Configure 27, Utils 17, including the category wrapper in each count. Overlapping clusters are deduplicated by stable subject/operation IDs.

Routing-only cases still need actual observable dispatch and file-read evidence. A response merely naming the desired route cannot pass. Required startup bookkeeping may occur in the owned fixture and must be recorded separately. Routing depth never authorizes executing the chosen feature, repair, migration or deployment operation.

Selecting only first-tier subjects does not test all their downstream workflows. Helpers needed to observe a legitimate handoff remain available, but their standalone behavioral cases are excluded. Conversely, a selected library skill may legitimately depend on startup, hooks, controllers or another skill; excluding that dependency's standalone tests cannot remove the dependency from execution. Full journeys intentionally cross skill boundaries. To avoid cross-family journeys, omit journey subjects or select only workflow subjects.

Exclusions remove the exact catalog members shown by `--list-clusters ... --format json`. For example, disabling `family:configure` removes its category/workflow subjects; it does not remove independent capability declarations or journeys from a `full` selection. Choose `scope:workflows` or a tier/family/skill selection when those are the desired coverage boundary. No runtime safeguard can be disabled through a cluster switch.

## Saved presets

| Preset | Selected chunk |
|---|---|
| `full` | Entire inventory and every applicable depth. |
| `first-tier` | Nine public commands, routing and entry-owned behavior. |
| `first-tier-routing` | Nine public commands, routing only. |
| `routing` | Routing/load paths across all workflows. |
| `internal-routing` | Five internal top-level routing/startup skills. |
| `library` | Every Tier 2 library workflow. |
| `hooks` | All hook registrations and event behaviors. |
| `capabilities` | All capability contracts through their callers. |
| `journeys` | All fifteen end-to-end journeys. |
| `recovery` | Recovery/Doctor/migration/startup skill group. |
| `corpus` | Corpus pipeline skill group. |
| `controlled-stories` | Small/large stories, John Wick, check-in and orchestrator. |

The catalog currently contains 366 named clusters and twelve presets. Exact stable memberships live in JSON, not a set of manually maintained copies of tests.

## Save a reviewable selection

```bash
python3 scripts/select_behavioral_clusters.py --preset routing --include family:build --format json --output /tmp/sweetclaude-build-routing-plan.json
```

Choose a fresh output path. The selector refuses to overwrite an existing file, the inventory, the catalog, or the input configuration. JSON output records resolved dimensions, enabled/disabled clusters, selected operation IDs, caller/wording forms, branch obligations, source-anchor and routing-edge IDs, nonoptional invariants, and subjects omitted as inapplicable. It also records the exact inventory SHA-256; a catalog bound to different inventory bytes is rejected.

The raw operation inventory retains its original 347 IDs and all its source obligations. Cluster selection is an overlay and does not delete those requirements. The plan's operation and subject counts are scope estimates. They are not counts of expanded or executed tests; the raw branch/profile-to-scenario mapping remains pending.

## Contract for the later behavioral runner

The runner consumes the selected plan and expands operation subjects into cases carrying their originating subject, layer, kind, entry, wording, profile and source obligations. It must prove every selected obligation is implemented or report it unimplemented. It must never silently substitute another test for an unimplemented selected path. `scripts/run_behavioral_e2e.py` implements this for Tier 1 routing and leaves other selected obligations explicit in its compiled manifest.

Disabled standalone cases must not be scheduled, including through a dependency resolver. Fixture setup and actual product runtime dependencies remain permitted within the selected case's declared authority; report them separately from selected coverage. Shared/transitive source obligations require explicit ownership mapping because the preview's direct-reference source IDs are a starting set, not a proof of complete dependency closure.

Report `not-selected` separately from `not-run`, `unimplemented`, `blocked-environment`, `oracle-gap`, `fail` and `pass`. A partial selection can pass only its selected implemented cases; it cannot satisfy full acceptance. Restore or cleanup failure remains a failure for the selected case. The full-suite baseline still requires all applicable paths and every unresolved coverage obligation to be reconciled.
