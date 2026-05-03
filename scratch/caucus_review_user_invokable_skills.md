# Caucus Review: Which SweetClaude Skills Should Be User-Invokable?
**Date:** 2026-05-03  
**Proctor:** SweetClaude Framework  
**Topic:** Categorize all SweetClaude skills as DEFINITELY user-invokable, DEFINITELY NOT user-invokable, or GREY AREA  
**Scope:** Slash-command menu visibility only — not whether skills can be called programmatically  
**Turns:** 3  

---

## Committee Profiles

### Priya Nair — Senior UX Research Lead, Developer Tools
*Figma, formerly Vercel. Specializes in progressive disclosure and cognitive load in complex CLI tooling. Published: "The Paradox of Choice in Developer Menus" (2024).*

**Known biases:**
- Believes a menu should only show what a first-time user can successfully act on without documentation. If an item requires context the user doesn't have yet, it shouldn't be in the top-level list.
- Strongly weights new-user experience over power-user convenience — she's seen abandonment rates spike with long menus.
- Dislikes "escape hatches" and workarounds; wants the primary path to be the obvious path.

**Blind spot:** Tends to over-protect users from advanced tools even after they've demonstrated readiness. Underweights the cost of capability discovery failure.

---

### Marcus Wellstone — Principal Architect & CLI Framework Maintainer
*Independent. 20 years building developer frameworks. Maintains three OSS CLIs with 10K+ monthly users.*

**Known biases:**
- Deeply allergic to hidden features. "I can ignore a long list. I cannot invoke what I don't know exists." Will resist every hide decision.
- Believes users who are smart enough to use a framework are smart enough to scroll a menu.
- Anchors to his own usage patterns — he is a power user, and he forgets that most users are not him.

**Blind spot:** Consistently underweights the 80% of users who are not framework experts. His argument is usually correct for himself and wrong for the median user.

---

### Ifeoma Okafor — Developer Experience Engineer, Lattice
*Specializes in onboarding flows, progressive disclosure, and tooling adoption. Ran DX programs at two YC-backed startups.*

**Known biases:**
- Default answer to hide/show debates is "tiered visibility" — expose different levels to different user profiles. Often proposes "why not both?" solutions.
- Believes hiding creates mystery that drives curiosity, not frustration.
- Always asks: "what is the user trying to accomplish?" not "what does the tool do?"

**Blind spot:** Her preferred solution (mode-based visibility) adds significant system complexity that small teams can't maintain. Often proposes the ideal over the practical.

---

### Dr. Søren Bjørnstad — Framework Design Researcher, Aarhus University
*Studies mental models in developer tooling. Publishes on conceptual coherence in complex software systems.*

**Known biases:**
- Argues that hiding symptoms doesn't cure the disease — if users are overwhelmed, the mental model is broken, not the menu length.
- Will question whether `user-invokable: false` addresses root cause or patches over a categorization problem.
- Leans theoretical; tends to propose taxonomy redesigns when the team needs a decision today.

**Blind spot:** Doesn't always account for reality that users won't read the docs and won't internalize mental models before their first session. Perfect taxonomy is not achievable under time pressure.

---

### Jamie Reyes — Indie Developer & Daily SweetClaude User
*Full-stack developer, solo founder. Uses SweetClaude on 3 active projects. Pragmatist.*

**Known biases:**
- "Ship it and learn." Believes a working heuristic today beats a perfect taxonomy tomorrow.
- Worried about maintenance burden — every hide/show decision creates a list that must be kept accurate as skills evolve.
- Has opinions formed by actual daily use, not theoretical user models.

**Blind spot:** Can accept "good enough" too quickly without thinking through the edge cases that will bite users. Sometimes mistakes familiarity for clarity.

---

## Skill Inventory (for reference)

**The 80 skills under consideration:**

| Skill | Description (abbreviated) |
|-------|--------------------------|
| adopt | Drop SweetClaude into inherited codebase |
| behavioral-regression | Validate framework's 15 behavioral contracts |
| code-debt | Tech debt cleanup with TDD |
| code-feature | Build a new feature end-to-end |
| code-issue | Implement a GitHub issue end-to-end |
| code-review | Code, security, compliance review |
| code-tdd | **Internal TDD process skill — "Not a direct user entry point"** |
| code-testing | Run test suite, mutation, security, PR pre-check |
| deploy-ship | SHIP phase skill, pre-ship checklist |
| design-api-design | Design API endpoints |
| design-architecture | Define system architecture |
| design-change-impact-analysis | Ripple-effect analysis for changes |
| design-data-model | Design data model |
| design-manage-decisions | Record/track design decisions |
| design-solutioning-gate | Validate solution before implementation |
| design-tech-spec | Technical specification |
| design-user-flows | Convert stories into UX flows |
| design-ux-review | Virtual UX review with persona subagents |
| design-ux | Define visual/interaction design |
| design-wireframes | Generate HTML wireframes |
| document-corpus | Manage document corpus pipeline |
| documents-academic-research | Academic paper development |
| documents-narrative-arc | Build strategic knowledge graph |
| documents-update-docs | Update docs when implementation changes |
| find-skill | Find and start the right skill |
| fix-sweetclaude | Audit and repair SweetClaude configuration |
| go | Figure out what to do next and do it |
| guardian-off | Disable Protocol Guardian |
| guardian-on | Enable Protocol Guardian |
| help | Interactive help assistant |
| hibernate | Hibernate/unhibernate project |
| init | Bootstrap SweetClaude infrastructure |
| john-wick-checkin | **Internal John Wick phase check-in subagent** |
| john-wick | Fully autonomous multi-session SDLC pipeline |
| master | **SweetClaude phase router, session entry point** |
| misc-meeting-prep | Prepare for a specific meeting |
| mockup-extract | Pull production component into sandbox |
| mockup-graduate | Move approved mockup into main app |
| mockup-sandbox | Create/iterate interactive UI mockups |
| next-steps | Walk through pipeline step by step |
| off | Deactivate SweetClaude for current project |
| on | Get started with SweetClaude on any project |
| product-brief | Write a product brief |
| product-competition | Competitive analysis |
| product-discovery | Establish what is being built and why |
| product-manage-scope | Track scope changes |
| product-market-messaging | Craft external messaging |
| product-milestones | Manage roadmap milestones |
| product-parking-lot | Manage deferred work |
| product-positioning-statement | Define product positioning |
| product-prd | Write a PRD |
| product-research | Survey the solution field |
| product-roadmap-analysis | RICE scoring and stack-rank analysis |
| product-sprint-plan | Plan a sprint |
| product-user-personas | Define product users |
| product-user-stories | Write user stories |
| product-user-tdd-tests | Transition user stories into Gherkin |
| project-backlog-triage | Structured backlog grooming |
| project-backlog | View/manage unscheduled backlog |
| project-epics | Manage epics |
| project-gh-import-issues | Import GitHub Issues to local store |
| project-gh-sync-issues | Bidirectional GitHub sync |
| project-goals | Manage project goals |
| project-issues | Manage project issues |
| project-mode | Assess and shift project mode |
| project-roadmap | Manage product roadmap |
| project-scope | Define and maintain project scope |
| project-sprints | Sprint planning, activation, board view |
| purge | Delete all SweetClaude artifacts |
| retro | Review improvement register |
| session-export | Export Claude.ai session as portable package |
| something-broke | Reactive production incident |
| status | Orient to current project |
| testing-accessibility | WCAG 2.1 Level AA audit |
| testing-compliance | Compliance control testing |
| testing-performance | Performance baselines and benchmarks |
| testing-plan | Define test strategy |
| testing-security | Structured security review / STRIDE |
| testing-session | Manual QA session |
| update | Update SweetClaude to latest version |
| usage | Toggle/view local usage tracking |

---

## Turn 1: Initial Categorization

**Proctor's question:** Without discussion yet — each panelist produces their initial gut-level categorization. Label each skill: **YES** (user-invokable), **NO** (internal/orchestration), or **GREY** (genuinely uncertain). Then name the 3-5 skills you feel most certain about and the 3-5 you find most ambiguous. We'll compare tallies before Turn 2.

---

### Priya Nair

My framework: a skill is user-invokable if a user could arrive at it cold — no prior framework knowledge — and successfully invoke it in the right context. If the skill exists to be called BY another skill, or if invoking it out of sequence would cause confusion or harm, it belongs off the menu.

**Clear NOs** — these are the easy ones:
- `code-tdd`: The description literally says "Not a direct user entry point." This is the platonic example of what `user-invokable: false` is for.
- `john-wick-checkin`: "Internal subagent." Not even a question.
- `master`: "Phase router." This is the framework's nervous system, not a user-facing command.
- `documents-update-docs`: Invoked during Verify phase by other skills. A user typing this cold would have no idea what it would update or when to call it.
- `design-solutioning-gate`: A gate is not a starting point. Users don't think in terms of "I want to validate my solution" — they think in terms of the work they're doing. This gets called FROM design skills.
- `design-change-impact-analysis`: Same pattern — this is a phase artifact check that belongs inside `code-feature` or `code-issue`.

**Ambiguous for me:**
- `go` vs `next-steps`: These appear to do the same thing. One of them is redundant. Which one stays visible?
- `guardian-on` / `guardian-off`: The Protocol Guardian is explicitly offered to users as a thing they can activate. But is it better as a menu item or as a response to being offered it?
- `find-skill`: This is meta-navigation, and I like meta-navigation tools being visible. But it implies the main menu is already broken if you need a skill to find the right skill.
- `product-user-tdd-tests`: This is a pipeline step inside `product-user-stories`. Should it be a standalone entry point?
- `design-manage-decisions`: Could be a utility a user reaches for at any time, or could be an internal record-keeping step. Depends on whether users think "I want to log a decision" proactively.

---

### Marcus Wellstone

I'll say it directly: I think hiding things is almost always wrong, and I'm going to vote YES for nearly everything. But I'll honor the exercise and look for things even I agree should be hidden.

**My clear NOs — and these better be a very short list:**
- `code-tdd`: Fine. It says it's internal. I believe it.
- `john-wick-checkin`: Subagent. Fine.
- `master`: Fine. Router, not a command.

That's it. Everything else? YES. Here's my argument: the users of SweetClaude are developers. They can scroll a menu. They can read a description. If they click the wrong skill they get a clarifying question — they don't get burned. The cost of hiding something useful is infinite (user can never discover it). The cost of showing something they don't need is near-zero (they scroll past it).

**What I find most ambiguous:**
- `go` vs `next-steps` — I'd show both and let users figure out which they prefer.
- `behavioral-regression` — most users will never need this, but the ones who do REALLY need it. Show it.
- `design-solutioning-gate` — I actually think a user might want to run this proactively. Show it.
- `fix-sweetclaude` — diagnostic tool, show it.
- `session-export` — this is useful and entirely hidden from the workflow. Show it.

---

### Ifeoma Okafor

I want to propose a frame before categorizing: there are three kinds of skills on this list, and the YES/NO question flattens them.

1. **Entry points** — where a user starts a session or a work stream. These MUST be in the menu: `go`, `on`, `help`, `status`, `code-feature`, `something-broke`, etc.
2. **Utilities** — skills a user might reach for proactively, mid-session, outside of any pipeline. These should be in the menu too: `project-issues`, `retro`, `misc-meeting-prep`, `session-export`.
3. **Pipeline steps** — skills that are called BY other skills as structured steps. These should be hidden: `code-tdd`, `john-wick-checkin`, `documents-update-docs`, `design-solutioning-gate`, `design-change-impact-analysis`.

The grey area is skills that are BOTH utilities AND pipeline steps. `product-user-tdd-tests` is a step inside `john-wick`, but also something a user might want to run standalone. `design-manage-decisions` is called by design skills but also something a user might reach for to log a decision outside a formal session.

My initial greens/greys:

**Clear YES:** `on`, `off`, `help`, `status`, `go`, `code-feature`, `code-issue`, `code-review`, `code-testing`, `something-broke`, `deploy-ship`, `init`, `update`, `purge`, `hibernate`, `adopt`, `john-wick`, `retro`, `session-export`, `misc-meeting-prep`, `mockup-sandbox`, `mockup-extract`, `mockup-graduate`, all `product-*`, all `project-*`, all `testing-*`, `design-architecture`, `design-tech-spec`, `design-data-model`, `design-api-design`, `design-ux`, `design-wireframes`, `design-user-flows`, `design-ux-review`, `behavioral-regression`, `usage`, `find-skill`, `document-corpus`, `documents-academic-research`, `documents-narrative-arc`, `fix-sweetclaude`, `code-debt`

**Clear NO:** `code-tdd`, `john-wick-checkin`, `master`

**Grey:** `go` vs `next-steps` (redundant?), `guardian-on`/`guardian-off` (modal toggles — do users want these in menus?), `design-solutioning-gate`, `design-change-impact-analysis`, `design-manage-decisions`, `documents-update-docs`, `product-user-tdd-tests`

---

### Dr. Søren Bjørnstad

Before I categorize, I want to name what I think is actually happening. You have ~80 skills and they've grown organically. The `user-invokable: false` feature is being used to patch a categorization problem — some of these skills should perhaps not exist as separate commands at all, but as *modes* within larger skills. `design-solutioning-gate` is not a skill, it's a phase within `design-architecture`. `documents-update-docs` is a step in the Verify phase, not a standalone capability.

My concern: if we hide things without redesigning the taxonomy, we're building a larger and larger hidden layer that becomes its own maintenance burden. But I'll give the practical answer the team needs today.

**Clear NOs:**
- `code-tdd`: Internal. Stated explicitly.
- `john-wick-checkin`: Internal subagent.
- `master`: Internal router.
- `documents-update-docs`: This is always invoked by context. A user typing this cold has no document to update.
- `design-solutioning-gate`: A gate is a phase check, not a starting verb for a user.
- `design-change-impact-analysis`: Invoked during VERIFY. Not a starting point.
- `next-steps`: This appears to duplicate `go`. One of these should be hidden or removed entirely.

**Most ambiguous — these reveal the deeper taxonomic confusion:**
- `guardian-on` / `guardian-off`: These exist because the guardian is offered as a choice, not selected from a menu. If users enable it through conversation, not slash commands, why are they in the menu at all?
- `product-user-tdd-tests`: Is this a user-facing step in a product pipeline, or a technical step inside `john-wick`? The name is technical but the purpose is product-facing.
- `find-skill`: If the menu works, this skill shouldn't need to exist. Its presence implies we've already conceded the menu is too long. Hiding it doesn't fix that.
- `design-manage-decisions`: Should decision logging be a standalone skill or a feature embedded in every design skill?

---

### Jamie Reyes

I'm going to be the practical voice. I use this thing every day. Here's what I actually invoke:

**Things I type directly, regularly:**
`status`, `go`, `code-feature`, `code-issue`, `code-review`, `something-broke`, `deploy-ship`, `retro`, `project-issues`, `product-brief`, `help`, `update`, `on`, `off`, `mockup-sandbox`

**Things I've typed maybe once:**
`init`, `purge`, `hibernate`, `adopt`, `behavioral-regression`, `testing-security`, `testing-accessibility`, `usage`, `fix-sweetclaude`, `session-export`

**Things I have NEVER typed and would be confused if I accidentally hit:**
`code-tdd`, `john-wick-checkin`, `master`, `documents-update-docs`, `design-solutioning-gate`, `design-change-impact-analysis`, `next-steps` (I use `go`)

**My honest assessment of the grey area:**
- `guardian-on`/`guardian-off`: I've seen these in the menu and never used them from there. I got offered the guardian in conversation and said yes. The menu items feel redundant.
- `find-skill`: I've never used this. If I don't know what skill to use, I just ask Claude in plain English. The skill feels like a workaround.
- `product-user-tdd-tests`: I've used this once when I wanted to jump straight to Gherkin without going through the full `product-user-stories` flow. So: grey. Useful but niche.
- `go` vs `next-steps`: I use `go`. I've never used `next-steps`. They read identically to me.
- `design-manage-decisions`: I've used this proactively mid-session. It's a utility I'd miss if it disappeared from the menu.

---

### Proctor Synthesis — Turn 1

**Position tally after initial categorization:**

| Skill | Priya | Marcus | Ifeoma | Søren | Jamie | Consensus |
|-------|-------|--------|--------|-------|-------|-----------|
| `code-tdd` | NO | NO | NO | NO | NO | **CLEAR NO** |
| `john-wick-checkin` | NO | NO | NO | NO | NO | **CLEAR NO** |
| `master` | NO | NO | NO | NO | NO | **CLEAR NO** |
| `documents-update-docs` | NO | — | GREY | NO | NO | **Leaning NO** |
| `design-solutioning-gate` | NO | YES | GREY | NO | NO | **Split** |
| `design-change-impact-analysis` | NO | — | GREY | NO | NO | **Leaning NO** |
| `next-steps` | GREY | YES | GREY | NO | NO | **Split** |
| `guardian-on`/`guardian-off` | GREY | YES | GREY | GREY | GREY | **Grey** |
| `find-skill` | GREY | YES | YES | GREY | NO | **Grey** |
| `product-user-tdd-tests` | GREY | YES | GREY | GREY | GREY | **Grey** |
| `design-manage-decisions` | GREY | YES | YES | GREY | YES | **Leaning YES** |

**What shifted:** There is broad consensus on 3 clear NOs (`code-tdd`, `john-wick-checkin`, `master`). The rest of the disputed skills cluster around two patterns:
1. **Pipeline steps masquerading as skills** — `documents-update-docs`, `design-solutioning-gate`, `design-change-impact-analysis`
2. **Modal/meta utilities** — `guardian-on/off`, `find-skill`, `next-steps` vs `go`

**Open questions entering Turn 2:**
1. Is there a principled distinction between `go` and `next-steps`? Is one redundant?
2. `guardian-on`/`guardian-off`: should these be in the menu at all, given the guardian is offered via conversation?
3. `design-solutioning-gate` and `design-change-impact-analysis`: can a user legitimately invoke these standalone, or are they always pipeline-internal?
4. `find-skill`: is the meta-navigation skill a sign the menu is already broken?

---

## Turn 2: Resolving the Grey Area

**Proctor's question:** We have 3 clear NOs locked. Now let's resolve the grey area by working through each contested skill specifically. For each: what is the user's verb? What would a user type in plain English to trigger this? If the answer is "I would never phrase it that way," it's probably a NO.

---

### Priya Nair

**The "user's verb" test is the right frame.** Let me apply it to each grey:

**`next-steps` vs `go`:** The user's verb for both is "what do I do next?" or "continue." These are genuinely synonyms from a user perspective. I side with Søren: one should be hidden. `go` is the verb I'd type. `next-steps` reads like a framework artifact — it names an internal process step, not a user intent. **My vote: hide `next-steps`.**

**`guardian-on`/`guardian-off`:** The user's verb is "enable strict mode" or "enforce the process." BUT — and this is important — the interaction model says the guardian is OFFERED via conversation. The user says "yes" and Claude enables it. If that's the primary activation path, why is there a slash command? I think these exist as a fallback — "I already said yes in a previous session, let me re-enable it." That's a valid use case. **GREY → YES. Keep them.** They're low-frequency but legitimate entry points.

**`find-skill`:** The user's verb is "I don't know what skill to use." That's a real verb! But — Søren is right that this skill's existence implies the menu is already broken. If the menu were perfectly organized, users would never need meta-navigation. However, given we HAVE 80 skills, meta-navigation is practical. **GREY → YES.** Show it.

**`design-solutioning-gate`:** The user's verb would be "validate my design" or "check my approach." That IS a real user intent. But the problem is: validate WHAT design? The skill needs design artifacts to exist before it runs. You can't invoke this cold. A user who types this without a running design session will hit confusion. **GREY → NO.**

**`design-change-impact-analysis`:** The user's verb would be "what will break if I change X?" That's a real verb. And unlike solutioning-gate, you CAN invoke this on any codebase at any time — you don't need a formal design session in progress. You just need code. **GREY → YES. Change my mind.**

**`documents-update-docs`:** The user's verb would be "update my docs." But: update them to reflect WHAT? This skill exists because something else changed. You don't walk up to your docs and say "update them" — you implement something and then update them. This is always downstream. **GREY → NO.**

**`product-user-tdd-tests`:** The user's verb would be "turn my user stories into Gherkin." That's a real verb and a real standalone need. I have stories. I want tests. I type this. **GREY → YES.**

---

### Marcus Wellstone

I want to push back on Priya's `next-steps` argument. She's saying hide it because `go` is more natural. But what if I specifically WANT the step-by-step walkthrough rather than the autonomous "just do the next thing" behavior of `go`? These might actually be different behaviors dressed in similar names. Before we hide `next-steps`, someone should read both skill files and confirm they're genuinely redundant.

**On `design-solutioning-gate`:** I hear the argument "you can't invoke this cold." But I invoke skills "cold" all the time and get prompted for the missing context. That's how all interactive CLIs work — you start it, it asks what it needs. I don't think "needs prior context" is a valid reason to hide something. **I vote YES.**

**On `guardian-on`/`guardian-off`:** Yes, show them. The fact that they're offered via conversation doesn't mean they shouldn't also be directly invocable. I want to be able to toggle the guardian mid-session without being "offered" it.

**On `find-skill`:** Yes. Obviously. Show it.

**On `documents-update-docs`:** Fine. This one I concede. Even I wouldn't type this cold. **NO.**

**My summary:** I'm conceding on `code-tdd`, `john-wick-checkin`, `master`, `documents-update-docs`. Everything else stays visible.

---

### Ifeoma Okafor

I want to introduce a distinction nobody has raised yet: **how does the user learn about these skills?**

There are two discovery paths:
1. **Menu browsing** — user opens the slash command picker and scans the list
2. **Contextual offer** — Claude says "you might want to run X now" mid-session

Some skills are primarily discovered via path 2. If a skill is ALWAYS surfaced contextually, showing it in the menu adds noise without adding discoverability value. If a skill is primarily discovered via path 1 (user goes looking), it MUST be in the menu.

**`guardian-on`/`guardian-off`:** Path 2 only. The Protocol Guardian offer is the primary activation path. I'm changing my vote to **NO for both**. Hide them. Users who want to invoke the guardian will invoke it through conversation, not by scanning a menu.

**`next-steps` vs `go`:** After reflection, I agree one should be hidden. The question is which. Let me read the descriptions more carefully mentally: `go` = "figure out what to do next AND do it" (autonomous). `next-steps` = "walk through pipeline step by step" (collaborative). These ARE different! `next-steps` is the slower, more deliberate mode. **Both should be visible.** I'm reversing my position. The user intent is different.

**`design-solutioning-gate`:** I side with Priya here. Context dependency is real. **NO.**

**`design-change-impact-analysis`:** I agree with Priya's reversal — this CAN be invoked on any codebase. **YES.**

---

### Dr. Søren Bjørnstad

Ifeoma's discovery-path distinction is taxonomically precise and I want to build on it. But I'll also name a third path nobody has mentioned:

3. **Workflow routing** — Claude invokes the skill on the user's behalf because the current phase requires it

Skills that are primarily reached via workflow routing should never be in the menu. They are internal to the state machine, not user-facing affordances. This resolves several greys cleanly:

- `design-solutioning-gate`: Workflow-routed. **NO.**
- `design-change-impact-analysis`: Workflow-routed during VERIFY, but also manually invokable (Priya's reversal is correct). **GREY remains.** I'll say **YES** with the caveat that the description should clarify it's also user-invokable.
- `documents-update-docs`: Workflow-routed. **NO.**
- `next-steps` vs `go`: Both are user-facing entry points with different interaction models. **Both YES.**

**On `guardian-on`/`guardian-off`:** Ifeoma's argument — "path 2 only" — is compelling. But Marcus's counter is also valid: what if a user wants to re-enable the guardian without going through the offer flow? I think the right answer is: **hide both, but document that you can also invoke them directly.** The menu is for discovery; documentation is for power users.

**My revised position:** Guardian NOs are correct. They are modal state toggles, not user commands. The analogy: you don't put "enable dark mode" in a command menu; you put it in settings.

---

### Jamie Reyes

Let me be concrete. Here's what I'd actually type and what I'd never type:

**Would I ever type `guardian-on` from the menu?** No. When the guardian comes up, it's because Claude offered it in conversation. I say "yes" in chat. The menu item is dead weight for me.

**Would I ever type `design-solutioning-gate`?** No. If I wanted to validate my design, I'd describe my design in the chat and ask Claude to poke holes in it. The skill exists for the formal pipeline.

**Would I ever type `next-steps`?** Sometimes, yes — when I want a more deliberate step-through rather than `go` just running something. They ARE different.

**Would I ever type `design-change-impact-analysis`?** Yes, actually. "What breaks if I change the auth middleware" is a thing I think about and would invoke.

**Would I ever type `product-user-tdd-tests`?** Yes. After writing stories manually, I want to jump straight to Gherkin. This is a valid standalone entry.

My revised votes:
- `guardian-on/off`: **NO** — never use from menu
- `design-solutioning-gate`: **NO** — pipeline-internal
- `documents-update-docs`: **NO** — pipeline-internal
- `design-change-impact-analysis`: **YES** — genuinely useful standalone
- `next-steps`: **YES** — different from `go`
- `product-user-tdd-tests`: **YES** — valid standalone step
- `find-skill`: **YES** — not everyone knows the skill names

---

### Proctor Synthesis — Turn 2

**What shifted:**

The committee reached convergence on several previously-grey skills:

| Skill | Turn 1 Status | Turn 2 Consensus | Key argument |
|-------|--------------|-----------------|--------------|
| `documents-update-docs` | Leaning NO | **NO (unanimous)** | Always downstream of a change; never a cold entry point |
| `design-solutioning-gate` | Split | **NO (4/5)** | Context-dependent; workflow-routed; can't invoke cold meaningfully |
| `guardian-on`/`guardian-off` | Grey | **NO (4/5)** | Primarily path-2 discovery (offered via conversation); menu adds noise not value |
| `next-steps` | Split | **YES (4/5)** | Different from `go` — deliberate step-through vs autonomous execution |
| `design-change-impact-analysis` | Leaning NO | **YES (4/5)** | Can be invoked on any codebase; "what breaks if I change X" is a real user verb |
| `product-user-tdd-tests` | Grey | **YES (4/5)** | Valid standalone entry for users with stories who want Gherkin |
| `find-skill` | Grey | **YES (4/5)** | Meta-navigation justified given 80-skill menu |
| `design-manage-decisions` | Leaning YES | **YES (unanimous)** | Utility a user reaches for proactively mid-session |

**Remaining unresolved:** None — the committee reached working consensus on all grey items.

**One open question for Turn 3:** Are there any other skills that should be examined? Marcus raised that EVERY design skill might have legitimate standalone use. The committee should briefly audit the full list to catch any missed NOes.

---

## Turn 3: Final Verdicts and the Complete List

**Proctor's question:** Produce the definitive three-column categorization. Any dissents should be registered now — they become the minority report. Also: are there any skills outside the grey area discussion that we missed?

---

### Priya Nair

I want to flag two skills we didn't discuss that I'd nominate as NOs:

**`john-wick`:** Wait — hear me out. This is the fully autonomous multi-session SDLC pipeline. It is an extraordinarily powerful and potentially destructive invocation for a first-time user. I'm not saying hide it forever. I'm saying: should we require users to discover it intentionally rather than stumble into it from a menu? A user who accidentally triggers john-wick could end up with a massive automated change session they didn't intend. **I'd vote GREY.** I won't fight this to the death, but it should be flagged.

**`behavioral-regression`:** This tests the framework itself against behavioral contracts. Most users will never need this. But I can imagine an advanced user explicitly wanting to run it after an update. **YES, keep it.** Power user tool.

**`purge`:** Shows all files and requires typing "I understand." This IS user-invokable — it's designed to require deliberate intent. **YES.**

**My complete NO list:** `code-tdd`, `john-wick-checkin`, `master`, `documents-update-docs`, `design-solutioning-gate`, `guardian-on`, `guardian-off`

**My GREY (edge case, lean NO but not fighting):** `john-wick`

---

### Marcus Wellstone

I'm registering my minority dissent on the guardian skills. **`guardian-on` and `guardian-off` should be in the menu.** My argument: the Protocol Guardian offer is a conversational UX pattern that could change or fail. Slash commands are reliable affordances. If you hide the guardian toggles, you're betting that the conversational offer always surfaces at the right time. That's a fragile bet.

But I'm in the minority (4-1), so I'll note the dissent and move on.

**On `john-wick`:** Priya's concern is valid but I disagree with the conclusion. `john-wick` is clearly labeled, clearly named, and users who invoke it will immediately see its scope. The answer to "powerful and potentially destructive" is not hiding — it's a prominent confirmation step inside the skill. Which, by the way, it should have if it doesn't. **YES.**

**My complete NO list:** `code-tdd`, `john-wick-checkin`, `master`, `documents-update-docs`, `design-solutioning-gate`

---

### Ifeoma Okahar

I want to add one more skill to the review: **`design-ux-review`**. This "spawns parallel subagents — one per persona — each walking through a flow or wireframe." It's a meta-skill that orchestrates sub-processes. BUT it IS a user-facing entry point — "I want UX review of my wireframes" is a real verb. **YES.**

Also flagging **`session-export`**: no pipeline calls this. It's a pure utility. **YES.**

I agree with the committee's NO list. My final additions: no new NOs from me.

**My complete NO list:** `code-tdd`, `john-wick-checkin`, `master`, `documents-update-docs`, `design-solutioning-gate`, `guardian-on`, `guardian-off`

---

### Dr. Søren Bjørnstad

I want to formally note the deeper issue the committee sidestepped: `design-solutioning-gate` and `design-change-impact-analysis` BOTH exist as standalone skills when they are logically PHASES within larger design skills. The `user-invokable: false` fix is correct short-term. The long-term fix is to absorb them into their parent skills as flags or modes. Same with `documents-update-docs`.

This is not a blocker for today's decision — `user-invokable: false` is correct for all three. I just want the taxonomy debt logged.

**My complete NO list:** `code-tdd`, `john-wick-checkin`, `master`, `documents-update-docs`, `design-solutioning-gate`, `guardian-on`, `guardian-off`

**Taxonomy debt note:** `design-solutioning-gate`, `design-change-impact-analysis`, and `documents-update-docs` should eventually be absorbed into parent skills rather than existing as hidden standalone entries.

---

### Jamie Reyes

Agreed on all NOs. Agreed `john-wick` should stay visible — it's powerful but intentional. Any user who types it is ready for it.

One more thing: I'd actually add **`next-steps`** to a soft GREY based on my usage. I've almost never typed it. I use `go`. They might genuinely be redundant in practice even if they're not redundant in design. I won't fight to hide it, but the framework maintainer should check if anyone ever uses `next-steps` once `go` exists. Usage analytics would answer this.

**My complete NO list:** `code-tdd`, `john-wick-checkin`, `master`, `documents-update-docs`, `design-solutioning-gate`, `guardian-on`, `guardian-off`

---

### Proctor — Final Synthesis

---

## Final Synthesis

### Position Trajectory

| Persona | T1 NOs count | T3 NOs count | Movement |
|---------|-------------|-------------|----------|
| Priya | 6 | 7 | +1 (added guardian-on/off) |
| Marcus | 3 | 5 | +2 (conceded guardian-on/off, documents-update-docs) |
| Ifeoma | 3 | 7 | +4 (conceded guardian-on/off, design-solutioning-gate, documents-update-docs) |
| Søren | 7 | 7 | Stable |
| Jamie | 6 | 7 | +1 (conceded guardian-on/off) |

### Consensus Findings

The committee reached unanimous or near-unanimous agreement on the following:

**DEFINITELY NOT user-invokable (hide with `user-invokable: false`):**

| Skill | Reason |
|-------|--------|
| `code-tdd` | Explicitly labeled internal in its own description. The platonic case. |
| `john-wick-checkin` | Internal subagent. Never a user entry point. |
| `master` | Phase router / session entry point — internal orchestration. |
| `documents-update-docs` | Always downstream of an implementation change; has no cold-entry use case. |
| `design-solutioning-gate` | Workflow-routed gate; context-dependent; not a user verb. |
| `guardian-on` | Primarily discovered via conversational offer, not menu scanning. Modal toggle, not a command. |
| `guardian-off` | Same as guardian-on. |

**DEFINITELY user-invokable (keep in menu) — unanimous or near-unanimous:**

All remaining ~73 skills, including specifically validated:
- `go` and `next-steps` (distinct behaviors: autonomous vs deliberate step-through)
- `find-skill` (meta-navigation justified at 80-skill scale)
- `design-change-impact-analysis` (standalone "what breaks if I change X" use case)
- `product-user-tdd-tests` (valid standalone entry for Gherkin generation)
- `design-manage-decisions` (proactive utility, not pipeline-only)
- `john-wick` (powerful but intentional; clearly labeled)
- `behavioral-regression` (power user tool, legitimately invoked after updates)
- `session-export` (pure utility, never pipeline-called)
- `guardian-on`/`guardian-off` — **see minority report**

### Unresolved Disagreements

**guardian-on / guardian-off (4-1 NO):**
- **Majority (Priya, Ifeoma, Søren, Jamie):** These are modal toggles discovered via conversational offer. Adding them to the menu adds noise without value — users who want the guardian say "yes" in conversation.
- **Minority (Marcus):** Slash commands are more reliable than conversational offers. Hiding these creates a fragile dependency on the offer UX working correctly every time. Users should be able to re-enable the guardian directly.

**`next-steps` (soft grey from Jamie):**
- Jamie suspects `next-steps` is practically redundant with `go` based on usage. The committee voted YES but recommends checking usage analytics once `usage` tracking is live. If `next-steps` shows near-zero invocations, reconsider.

### Prioritized Recommendations

1. **Apply `user-invokable: false` immediately** to: `code-tdd`, `john-wick-checkin`, `master`, `documents-update-docs`, `design-solutioning-gate`, `guardian-on`, `guardian-off`

2. **No changes needed** to all other skills — they are legitimately user-invokable.

3. **Monitor `next-steps` usage** once usage analytics are live. If near-zero after 30 days of real use, hide or merge into `go`.

4. **Log taxonomy debt:** `design-solutioning-gate`, `design-change-impact-analysis`, and `documents-update-docs` should eventually be absorbed into parent skills as modes/flags rather than existing as standalone (even hidden) skills. This is future work, not today's work.

5. **Add confirmation gate to `john-wick`** if it doesn't already have one, given Priya's concern about powerful unintended invocations.

### Minority Reports

**Marcus Wellstone dissents on `guardian-on`/`guardian-off`:**
> "Hiding the guardian toggles makes the Protocol Guardian feature dependent on a conversational UX path that could fail silently. If the guardian offer doesn't trigger, users have no way to enable it without remembering to type the slash command from memory. Slash commands exist precisely because discoverability via menus is more reliable than discoverability via conversation context. These should stay in the menu. I'd rather have a slightly longer menu than a feature that's unreachable in edge cases."

---

*Caucus complete. 3 turns. 5 experts. 7 clear NOs established. No disputed remaining items except the guardian minority report.*
