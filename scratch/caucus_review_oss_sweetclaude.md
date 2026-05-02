# Expert Caucus: SweetClaude as an Open Source Project + README Review

**Date:** 2026-05-01
**Proctor:** SweetClaude Caucus System
**Scope Constraint:** T1–T3: SWOT analysis on making SweetClaude successful as an open source project. T4–T6: Focused review of the README specifically.
**Documents reviewed:** README.md, CONTRIBUTING.md, how-it-works.md
**Total turns:** 6

---

## Committee

### 1. Nadia Okonkwo
**Title:** Independent OSPO Consultant; formerly Director of Open Source Programs, Google Cloud
**Expertise:** Nadia spent 12 years building contributor funnels, documentation strategies, and OSS health metrics programs. She helped launch 8 major OSS projects at scale, ran community health dashboards for 200+ repos, and now advises startups and mid-stage companies entering the OSS space. She has written the canonical "OSS Launch Readiness" checklist used at 40+ companies.
**Known biases:**
- Docs-first orthodoxy: "A project without documentation is a private project with a public URL."
- Dismisses "build it and they will come" — won't accept that organic growth is a strategy.
- Occasionally undervalues technical depth when community and documentation tell a simpler story.
**Focus areas this review:** Contributor funnel health, documentation strategy, launch readiness, community onboarding signals.

---

### 2. Marcus Löfgren
**Title:** Independent OSS Sustainability Researcher; creator of 3 projects with 50K+ GitHub stars (retired from 2 due to burnout)
**Expertise:** Marcus has shipped, scaled, and abandoned OSS projects across two decades. He co-authored "The Maintainer's Burden" (2024), the most cited empirical study on why OSS projects die, which showed that 71% of abandoned projects had a single critical-path contributor at time of failure. He runs a consulting practice helping OSS maintainers build bus-factor resilience and graceful deprecation plans.
**Known biases:**
- Maintenance-burden pessimist: evaluates every feature by the maintenance cost it creates, not just the value it delivers.
- Bus factor hawk: will always ask "what happens if the sole maintainer disappears?"
- Tends to foreground costs over benefits when evaluating contributions or architecture choices.
**Focus areas:** Maintenance sustainability, bus factor, long-term viability, what makes projects fail at the 18-month mark.

---

### 3. Priscilla Tan
**Title:** Senior Developer Advocate, JetBrains; leads DX audit programs for OSS partner integrations
**Expertise:** Priscilla has audited the developer experience of 60+ OSS tools for JetBrains' integration program. She specializes in time-to-first-value (TTFV): measuring the gap between "I found this project" and "I got something useful out of it." She is known for her blunt DX scorecards and has helped 12 projects reduce first-session drop-off by more than 50%.
**Known biases:**
- TTFV obsessive: "If I haven't seen value in 10 minutes, you've lost me — and most developers too."
- Dismissive of features that don't reduce friction in the first 30 minutes.
- Occasionally undervalues power-user features requiring investment before payoff.
**Focus areas:** Onboarding experience, first-session success rate, cognitive load of the README, install friction.

---

### 4. Dmitri Volkov
**Title:** Open Source Policy Director, Software Freedom Conservancy; 15 years in copyleft enforcement and OSS governance
**Expertise:** Dmitri has spent 15 years on OSS licensing disputes, foundation governance, and commercial platform dependency analysis. He has represented projects in 7 copyleft enforcement actions, advised 30+ projects on foundation structure vs. company control tradeoffs, and written extensively on the governance risks created when OSS projects depend on commercial AI platforms.
**Known biases:**
- AGPL zealot: "Copyleft is a gift to the commons — every permission you add is a right you're giving away."
- Suspicious of OSS projects with hard commercial platform dependencies ("platform risk is not a minor concern").
- Tends to see governance risks others miss; can be dismissed as alarmist.
**Focus areas:** License fitness for purpose, commercial platform dependency risk, governance model, contributor agreement structure.

---

### 5. Yuki Hashimoto
**Title:** Associate Professor, University of Tokyo; researcher in OSS sustainability of AI-assisted and AI-dependent projects
**Expertise:** Yuki has published 3 papers on platform dependency risk in AI-tooling OSS, including "When the Model Changes: Behavioral Drift in Prompt-Driven Open Source Tools" (2025). She runs a longitudinal study of 200 AI-adjacent OSS projects tracking how model version changes affect project viability and contributor behavior. Her work is cited by the AI governance community as the primary empirical base for understanding commercial AI platform dependency risk in OSS.
**Known biases:**
- Empirically driven: "Cite the paper or don't make the claim."
- Concerned about commercial-AI-platform dependency risk as an existential OSS threat vector.
- Can be overly skeptical of qualitative success assessments that lack measurement rigor.
**Focus areas:** AI-platform dependency risk, behavioral stability across model versions, what makes AI-tooling OSS projects durable vs. brittle, measurement gaps.

---

## Turn Agenda

| Turn | Focus |
|------|-------|
| T1 | OSS Strengths and Weaknesses |
| T2 | OSS Opportunities and Threats |
| T3 | SWOT synthesis + prioritized OSS success recommendations |
| T4 | README: first impression, structure, audience targeting |
| T5 | README: specific gaps, misleading claims, friction points |
| T6 | README: final verdict + concrete rewrite recommendations |

---

---

# Turn 1: OSS Strengths and Weaknesses

**Proctor framing:** We are evaluating SweetClaude as an open source project, not as a product. The question this turn is not "does the product work?" but "does this project have what it takes to survive and grow as an OSS community?" Look at the code structure, documentation state, contributor surface, license choice, and what this project is asking of prospective contributors. What does it have going for it? Where does it fall down?

---

**Nadia Okonkwo:**

I've reviewed the README and CONTRIBUTING.md with fresh eyes, and I'm going to start with the strength that matters most to OSS launch success: **SweetClaude has a clear audience signal**. The opening paragraph says "not for everyone" and names exactly who it *is* for. This is rare. Most OSS projects write for everyone and land with no one. SweetClaude has made a bet on early-stage founders, technical solopreneurs, and senior ICs. That is a community you can actually reach, because it is specific enough to have watering holes — places people in this group congregate online. That's the first prerequisite for word-of-mouth growth, and this project has it.

The second strength: **CONTRIBUTING.md shows meaningful thought about contributor segmentation**. The "good first contributions" table explicitly identifies isolated skills as the entry surface, and warns newcomers away from the hook system and migration architecture until they've built up understanding. This is the architecture of a contributor funnel — not just a "PRs welcome" statement. It will not attract the tsunami of first-time contributors alone, but it gives serious contributors an honest ramp.

The weaknesses are structural. **There are no community artifacts.** No GitHub Issues with "good first issue" labels. No Discussions space. No community standards file (SUPPORT.md, CODE_OF_CONDUCT.md). No response time expectations. No release cadence. These are the signals a new contributor looks for to assess whether this project is alive and whether their contribution will be seen. An empty Issues tracker is ambiguous — is there no feedback because it is perfect, or because no one is using it? Community health infrastructure reduces that ambiguity, and this project has none of it visible.

**The docs surface gap is significant.** The user guide has several files referenced that don't appear to exist yet — walkthroughs.md, faq.md, phases-and-workflows.md, tdd.md. Every broken link in the docs is a door that closes in a new contributor's face. This will not affect existing power users, but it will affect the 90% of evaluators who are doing a 10-minute assessment.

---

**Marcus Löfgren:**

I'm going to offer a less charitable reading.

The strength I'll grant: **this project is architecturally honest about what is deterministic and what is not**. The Enforcement Tiers section in how-it-works.md explicitly separates hook-enforced properties from instruction-guided properties. That is a level of epistemic honesty about probabilistic AI systems that I rarely see. It tells contributors exactly where the load-bearing elements are, which means they can reason correctly about what to change and what to leave alone. Most AI-tooling projects pretend everything is equally reliable. This one doesn't.

But I want to name the bus factor problem plainly, because the README signals it: "Built by an enterprise CTO/CISO and serial entrepreneur, originally as his toolchain." This is not a critique of the person — it is a description of the project's existential risk. This is a one-person project where the architecture, the skills, the hooks, the migration logic, and the contribution review process all route through one individual. CONTRIBUTING.md correctly identifies that the hook system and migration-registry.yaml require full framework knowledge. What it does not say is: *who currently has that knowledge?* The answer, as best I can tell from public artifacts, is: one person.

The average lifespan of a solo-maintainer OSS tool is 18–24 months from first significant public adoption to maintainer burnout or abandonment. SweetClaude has not yet acquired significant public adoption, so the clock hasn't started — but the architecture already resembles every project I've watched die. There is no evidence of a second person with full framework knowledge. The CONTRIBUTING.md does not mention a technical steering committee, a co-maintainer program, or a pathway to escalating contributors to the core architecture team.

This is fixable — but it requires proactive action *before* the project is popular, not after.

---

**Priscilla Tan:**

My lens is the 10-minute test: can I, as a developer who just discovered this project, understand what it does, decide if it's for me, and get something working — all within 10 minutes?

The partial strength I'll acknowledge: **the install process is genuinely simple**. Three commands — clone, cd, install.sh. The prerequisites table is honest (Claude Code is a paid dependency — more on that in a moment). The "Quick Try" option for a single session without installing reduces commitment friction. That's thoughtful.

Now the weaknesses. **The cognitive load of the README is very high.** I counted 14 separate major sections with 80+ commands listed in tables. The README is comprehensive — it reads like documentation, not marketing. That is a problem for first impressions. Most developers who hit a long README skim the first screen, look for a quick demo or screenshot, and make a bounce-or-stay decision in under 30 seconds. This README does not have a quick-win visual hook. No demo GIF. No "here's what this looks like in 30 seconds" section. No before/after comparison.

The other friction I'm flagging: **the dependency structure creates a non-obvious barrier**. Claude Code is required, and Claude Code requires an Anthropic subscription. This is not buried — it's in the prerequisites table — but the cost signal is not surfaced prominently. A developer spending 10 minutes evaluating this project needs to know "this requires a paid subscription to Anthropic's API or Claude.ai" in the first two paragraphs, not buried in a table they may skim past. When they discover the cost later, they feel deceived, not informed.

---

**Dmitri Volkov:**

I will focus on what others have left unaddressed: **the license choice is defensible but the platform dependency is not.**

The AGPL-3.0-or-later license is the correct choice for a project that is a plugin to a commercial platform. If this were MIT, Anthropic or any other commercial actor could fork it, close it, and productize it without contributing back. AGPL closes that path. This was a deliberate and correct choice.

But the license alone cannot address what I see as the fundamental governance risk: **SweetClaude has a hard dependency on Claude Code, which is a commercial product controlled by Anthropic, a for-profit company**. This is not a partnership of equals. Anthropic can change the plugin API, deprecate it, or shut it down entirely, and SweetClaude would stop functioning. The AGPL protects the code; it does not protect the project from platform obsolescence.

This is a known and accepted risk in commercial-platform OSS — it's the same risk that created the entire VSCode extension ecosystem. But there is a governance question SweetClaude has not yet answered: **what is the contingency if Anthropic changes the plugin architecture?** There is no mention of a compatibility layer, a migration strategy, or even acknowledgment that this risk exists. An OSS project that depends on a commercial platform owes its community a documented answer to "what happens if the platform changes?"

I'll also note that the Superpowers dependency (also required for full install) has a MIT license and is community-maintained — a different risk profile. But it is underdocumented in terms of what SweetClaude uses from it, which makes it opaque to contributors.

---

**Yuki Hashimoto:**

I want to build on Dmitri's point with empirical grounding.

In my research on AI-adjacent OSS projects, the most reliable predictor of project abandonment is what I call **behavioral stability risk**: when the underlying AI model changes, the project's documented behaviors change in ways maintainers cannot predict. SweetClaude is interesting because it has actually thought about this — the `behavioral-regression` skill explicitly exists to detect "silent behavioral drift" after model upgrades. That is a strength I have not seen in any other project in my study corpus. Most AI-tooling OSS projects treat model upgrades as non-events; this one treats them as a risk to be tested.

However, the strength partially undermines itself. The behavioral regression suite has 15 contracts, and the SKILL.md file (from what I can read in the references) correctly notes that instruction-guided properties are probabilistic. But **the behavioral regression test suite is manual** — it requires someone to run it and interpret the results. There is no CI integration, no automated running on model version changes, no documented process for what happens when a contract fails. The tool exists; the process around the tool does not.

The research implication is stark: projects that have the right tool but no process around it tend to not run the tool when it matters most — exactly during the time pressure of a model upgrade or a breaking change. If SweetClaude is serious about behavioral stability as a value proposition, it needs a process, not just a test suite.

The second gap I'll name: the project has no quantitative health metrics. No link to a GitHub Insights page, no contribution frequency tracking, no statements like "we process PRs within X days." This matters for OSS sustainability research because it means no one — not contributors, not users, not potential co-maintainers — can assess project health from the outside. This is a documentation gap with real consequences.

---

**Proctor synthesis — Turn 1:**

**Position tally:**
- Nadia: Positive on audience clarity and CONTRIBUTING.md structure; critical on missing community infrastructure
- Marcus: Positive on enforcement tier honesty; critical on single-maintainer bus factor
- Priscilla: Positive on install simplicity; critical on README cognitive load and cost signal
- Dmitri: Positive on AGPL choice; critical on commercial platform dependency governance
- Yuki: Positive on behavioral-regression skill existence; critical on manual process and no automated CI integration

**Emerging consensus:**
1. The project has unusually strong documentation for its stage — but it is reference documentation, not marketing documentation.
2. The bus factor / solo maintainer problem is the most frequently named existential risk.
3. The product's honest treatment of deterministic vs. probabilistic enforcement is a genuine strength others in the space don't share.

**Key tensions entering T2:**
- Is the commercial platform dependency a meaningful risk for OSS sustainability, or is it an accepted known tradeoff (VSCode extension model)?
- Is the missing community infrastructure a launch readiness issue or a normal early-stage gap?

---

---

# Turn 2: OSS Opportunities and Threats

**Proctor framing:** Turn 1 mapped what the project has and doesn't have internally. This turn is external: what is the environment SweetClaude is launching into? Where are the tailwinds? Where are the external forces that could kill or constrain the project? Marcus already named the 18-month burnout risk — that's internal. I want the external threats: competitive, ecosystem, platform, regulatory, cultural. What's in the environment that could accelerate or kill this?

---

**Priscilla Tan:**

The largest opportunity is **market timing**. The "structured AI coding workflow" category does not have a clear winner yet. Cursor owns fast autocomplete. GitHub Copilot owns IDE integration. But "I want AI to take me from idea to shipped code with discipline" — that space is open. There are category-defining windows in developer tools, and this one looks like it's open right now. SweetClaude is positioned directly in it.

The adjacent opportunity is **the growing disillusionment with vibe coding**. There is a visible and growing discourse among senior developers — the exact audience SweetClaude targets — that AI coding tools produce fast garbage. Stack Overflow surveys, Hacker News threads, r/ExperiencedDevs — the sentiment is "I can write a lot of code very fast, but it doesn't hold together." SweetClaude's pitch is a direct answer to that problem. The cultural moment is there if the project can reach it.

The threat in my lane is **attention competition from full-stack commercial offerings**. Devin, the emerging crop of "autonomous agent" products, and whatever Anthropic ships next can all reach this audience with a faster install, a polished UI, and marketing budgets. SweetClaude's edge is structure + discipline + open source + no vendor lock-in. If any commercial competitor ships even 60% of the workflow with zero install friction, SweetClaude's first-impression problem becomes existential.

---

**Marcus Löfgren:**

The opportunity I see is in a demographic that has not been well served: **the solo technical founder who is also the CTO**. This person has typically used professional-grade tools (Jira, Confluence, etc.) at scale, knows what they need, but is now operating alone and doesn't need enterprise complexity. SweetClaude is exactly the right abstraction for this person. It provides the rigor without the overhead.

But I want to name the threat I'm most concerned about, which nobody has said yet: **Anthropic itself is the biggest external threat**. Anthropic has the resources, the model access, and the product direction to build SweetClaude's feature set natively. If Anthropic ships a "project lifecycle manager" feature into Claude Code — a not-unreasonable product direction for them — SweetClaude's market position collapses overnight. Not because Anthropic would copy SweetClaude specifically, but because they would absorb the demand.

The OSS protection against this is usually the community: if SweetClaude has a committed user base, they will continue using and contributing to the open-source version even if a commercial alternative ships. But SweetClaude has not yet built that community. Which means it is currently in its most vulnerable window: technically capable but without the community moat that protects most open source projects from platform absorption.

---

**Dmitri Volkov:**

Picking up on Marcus's point — the Anthropic risk is real and I want to frame it more precisely for governance purposes.

There are two distinct vectors here. The first is product displacement (Marcus's point): Anthropic builds the feature natively. The second is **API deprecation risk**: Anthropic changes the plugin architecture, deprecates the slash-command interface, or imposes new restrictions on CLAUDE.md-based customization. SweetClaude's entire architectural foundation — slash commands, CLAUDE.md rules, hook invocation — sits on Anthropic's extension API. There is no guarantee of backwards compatibility.

The opportunity I want to name is **the governance vacuum in AI-tooling OSS**. There is currently no accepted governance model for OSS projects that are cognitive extensions of commercial AI platforms. The AI tooling space is producing a lot of projects structured like SweetClaude — instruction-file plugins — and there is no precedent for how they should be governed, what their licensing obligations are when the underlying model is proprietary, or what contributor rights look like. SweetClaude, as a serious early-stage project with a documented design rationale, has an opportunity to **define that governance model** and become a reference point for others in the category. That is a positioning opportunity beyond the product itself.

---

**Nadia Okonkwo:**

Picking up on Dmitri's governance point: there is an ecosystem opportunity I want to surface that others haven't addressed yet. **SweetClaude can become the default workflow layer for the emerging Claude Code extension ecosystem.** As more developers build skills and plugins for Claude Code, SweetClaude can become the "if you want a structured workflow, start here" recommendation. This is how many OSS frameworks achieved breakout adoption — not by winning users one at a time, but by becoming the default for a category of users within an existing ecosystem.

The threat from my lane: **the documentation debt is an acquisition barrier that will compound over time.** The missing user-guide pages (walkthroughs.md, faq.md, phases-and-workflows.md) are currently a minor problem because the project is early-stage. They become a major problem when SweetClaude gets a Hacker News post or a developer newsletter mention. Spikes of attention are the OSS acquisition mechanism — you get them rarely and briefly. If a spike hits before those pages exist, the bounce rate will be catastrophic and the reputation formed in that spike will be hard to change. The window for fixing documentation before first major attention spike may be small.

---

**Yuki Hashimoto:**

Building on what I said in Turn 1 about behavioral stability: the biggest external threat I see in my research domain is **model version churn**. Anthropic releases new Claude versions frequently. Each release can silently change the behavioral properties that SweetClaude documents as guarantees. The project has a behavioral regression suite — but without CI automation, each model upgrade is a manual fire drill.

The opportunity here is to lean into this as a distinguishing feature. **No other AI-tooling OSS project has a published, replicable behavioral contract test suite.** If SweetClaude automated this and published model-version-tagged compliance reports ("these 15 contracts passed on claude-sonnet-4-6, these 2 degraded on claude-opus-4-7"), it would become the trust infrastructure for the entire category. Other projects would cite SweetClaude's test results. Researchers would use it. Enterprise adopters — who are risk-averse about AI behavioral stability — would find it compelling.

The counter-threat: if SweetClaude does not invest in this, and a behavioral regression causes a visible failure for an early adopter who writes about it publicly, the trust reputation is very hard to recover.

---

**Proctor synthesis — Turn 2:**

**Opportunities identified:**
1. Market timing — the structured AI workflow category is open and the cultural moment (vibe coding disillusionment) is favorable
2. Underserved solo technical founder / CTO demographic
3. Potential to become the default workflow layer in the Claude Code extension ecosystem
4. Governance model definition opportunity for AI-tooling OSS
5. Behavioral contract testing as trust infrastructure and competitive differentiator

**Threats identified:**
1. Anthropic product absorption — native feature built into Claude Code
2. Anthropic API deprecation — plugin architecture changes
3. Attention spike hitting before documentation gaps are filled
4. Model version churn with manual-only regression testing
5. Commercial competitors (Devin, autonomous agents) capturing the same audience with less friction
6. Bus factor / solo maintainer exhaustion (crossed over from T1, but named again)

**Key tension sharpened:** The behavioral regression test suite is simultaneously the project's most distinctive OSS strength and its most visible execution gap. Multiple panelists converged on this independently.

**Open questions entering T3:**
- Which of the five opportunities is the highest-leverage first move?
- Does the Anthropic platform dependency risk require active mitigation, or is it acceptable as a known tradeoff?

---

---

# Turn 3: SWOT Synthesis + Prioritized OSS Success Recommendations

**Proctor framing:** We have now mapped the full SWOT landscape. This turn is synthesis and prescription. I want each panelist to identify what they believe is the single highest-leverage action SweetClaude should take in the next 90 days to improve its OSS success trajectory. Then I want the group to debate and prioritize. We need to leave this turn with a ranked list.

---

**Priscilla Tan:**

My recommendation: **build one end-to-end demo video or GIF before the first public attention spike.**

The structural problem with SweetClaude's acquisition is that it requires someone to understand the entire lifecycle to see the value. The README description is accurate but abstract — "discovery-first pipeline," "TDD enforcement at four levels," "compliance context flows through architecture." These are correct descriptions. They are not demonstrations.

A 90-second terminal recording of the actual experience — someone running `/sweetclaude:on` on an empty folder, answering three questions, watching a product brief appear, then a skeleton architecture — would do more for first-impression acquisition than any documentation improvement. Show, don't tell. This is the highest-leverage action per unit of effort in the first 90 days.

Responding to Marcus's T1 point: I agree the bus factor is a long-term problem, but it is not a 90-day action item. The 10-minute DX problem is an immediate acquisition risk. Fix acquisition first, sustainability second — a project with no users doesn't need a co-maintainer program.

---

**Marcus Löfgren:**

I respectfully disagree with Priscilla's sequencing. A demo video attracts users. It does not create sustainability. And an unsustainable project with users is worse than an unsustainable project without them — the abandonment is more visible and more damaging.

My recommendation: **identify and onboard one technical co-maintainer with full framework knowledge in the next 90 days.**

This is the most important thing that can be done for OSS project longevity, and it requires effort *now* — before the project is popular. Finding co-maintainers after your project has 5,000 stars is much harder than finding one at 500, because at 5,000 stars your GitHub issue backlog is overwhelming and potential co-maintainers see unmanageable work. At 500 stars, the project is small enough that a motivated person can read the entire codebase in a weekend.

The concrete ask: post a "Looking for Co-Maintainer" issue with a specific description of what "full framework knowledge" means (the What Requires Full Framework Knowledge table in CONTRIBUTING.md is a good starting point), what the time commitment looks like, and what decision-making authority a co-maintainer would have. This is not a contribution request — it is a partnership request.

---

**Nadia Okonkwo:**

I want to prioritize differently from both Priscilla and Marcus, and I want to explain why.

My recommendation: **fill the documentation gaps before the first attention spike — specifically, write walkthroughs.md and faq.md.**

The README currently links to five documentation pages that don't exist: walkthroughs.md, faq.md, phases-and-workflows.md, tdd.md, and corpus-system.md. Every outbound link from the README that lands on a 404 is a trust damage event. The project cannot control when its first attention spike arrives — an HN post, a tweet from a developer influencer, a mention in a newsletter. When that spike hits, the documentation state is what users encounter. If those pages aren't ready, the impression set in that window is "promising but incomplete" — and that impression lingers.

I hear Marcus on co-maintainer, and I'll agree that's important. But a co-maintainer cannot be found until there's something worth maintaining to show them. The documentation is part of what makes the project look worth co-maintaining. These two actions are sequential, not parallel — fix documentation first, then recruit.

---

**Dmitri Volkov:**

I want to name a recommendation neither Marcus nor Nadia has raised: **publish a platform dependency policy document.**

Not because it is the most exciting 90-day action, but because it is the most neglected risk. The AGPL license was chosen correctly — but the license protects the code, not the project. If Anthropic changes the plugin architecture, the AGPL-licensed code still exists but the project stops working. Users deserve to know what the contingency is.

A platform dependency policy is a one-page document that answers: what does SweetClaude depend on (Claude Code, Superpowers, mcp-local-rag), what is the failure mode for each dependency, what is the contingency plan (or explicit acknowledgment that one doesn't exist), and what triggers would lead the project to reconsider the architecture. This is transparency, not defeatism. It also directly addresses Yuki's concern about behavioral stability across model versions — it gives the project a place to document what happens when a behavioral regression fails.

This is a positioning action as much as a governance action. An OSS project that has written a clear-eyed dependency risk policy is more trustworthy than one that has not.

---

**Yuki Hashimoto:**

I'm going to push back on prioritization and propose a different framing.

The committee is debating whether documentation, co-maintainer recruitment, DX, or governance policy is the highest-leverage action. I think this debate is based on a false premise: that these actions compete for the same constraint. They do not. Documentation gaps and DX are fixed by one person in one week. Co-maintainer recruitment is an ongoing background activity. A platform dependency policy is a one-day writing exercise. These actions are not in tension.

If I must name a single highest-leverage recommendation: **automate the behavioral regression test suite against a CI trigger tied to model version tags.**

Here is my reasoning. Every other action on the table is table stakes — things most serious OSS projects do. Documentation gaps get filled. Co-maintainers get found. READMEs get improved. These are routine. The behavioral regression suite is not routine. It is the thing SweetClaude has that no other project in this category has. Automated behavioral regression testing against model version changes is a genuine contribution to the field — researchers would cite it, enterprise adopters would trust it, and the project would become the reference implementation for "how to manage behavioral stability in AI-dependent OSS."

This is the action that makes SweetClaude different, not just better.

---

**Marcus Löfgren:**

Yuki's reframe is partly correct — the actions aren't all competing for the same resource. But I'll push back on the CI automation recommendation as the single highest-leverage action. Automated behavioral regression CI requires a Claude Code API test harness that doesn't currently exist. It is not a one-week action — it is a multi-week architectural project. During that project, the bus factor is still one person.

The co-maintainer search costs no engineering time. It costs 30 minutes to write the issue and then ongoing attention to responses. It should be running in the background regardless of what else the project is working on.

---

**Nadia Okonkwo:**

Final position: I'll revise my sequencing based on the discussion. The actions are:

1. Fill documentation gaps (walkthroughs.md, faq.md, phases-and-workflows.md) — one person, one week
2. Launch co-maintainer search — 30 minutes + ongoing
3. Demo video or terminal recording — one day
4. Platform dependency policy — one day writing
5. Behavioral regression CI automation — multi-week engineering project, high value, later

This is a sequenced road map, not a prioritized list where only one action matters.

---

**Proctor synthesis — Turn 3:**

**SWOT Summary:**

| | Positive | Negative |
|---|---|---|
| **Internal** | Precise audience targeting; enforcement tier honesty; AGPL choice; CONTRIBUTING.md contributor segmentation; behavioral-regression skill; simple install | Solo maintainer/bus factor; missing community infrastructure; documentation gaps (5 broken links); no community metrics |
| **External** | Market timing (open category); cultural moment (vibe coding fatigue); Claude Code ecosystem positioning; governance model leadership opportunity; behavioral contracts as trust infrastructure | Anthropic product absorption risk; plugin API deprecation risk; attention spike before docs ready; model churn with manual-only regression; commercial autonomous agents |

**Recommended actions (sequenced by effort/urgency):**

1. **Fill the 5 broken documentation links** — immediate, one week effort, blocks acquisition
2. **Launch co-maintainer search issue** — 30 minutes, run in background, long-term sustainability
3. **Produce one demo recording** — one day, highest acquisition impact per unit effort
4. **Publish platform dependency policy** — one day writing, governance transparency
5. **Automate behavioral regression CI** — multi-week, highest differentiation value, deferred but important

**Unresolved disagreements:**
- Marcus and Priscilla disagree on whether sustainability (co-maintainer) or acquisition (demo) should come first when both are needed. The committee majority favors the sequenced view over the ranked-priority view.

---

*Checkpoint: caucus_checkpoint_turn3.md written.*

---

---

# Turn 4: README — First Impression, Structure, and Audience Targeting

**Proctor framing:** We pivot now to the README specifically. This is a fresh read. Forget the OSS analysis — pretend you just found this project on GitHub. You're a developer who matches the stated target audience: early-stage founder or senior IC. You've landed on the README. First 30 seconds, first impression, structure decisions. What works? What doesn't? What is the README trying to be, and does it succeed?

---

**Priscilla Tan:**

First 30 seconds, honest reaction:

The opening paragraph is the best part of this README. **"Not the right tool for everyone"** in the first sentence is genuinely unusual and immediately trustworthy. Most projects spend the first paragraph claiming they solve everything for everyone. This one does the opposite. As someone who spends my career auditing onboarding experiences, I know that selective trust signals — "this is not for you if X" — dramatically increase conversion for the users who are actually in scope. This opening is a DX win.

Then the README continues for 350 lines.

That is the structural problem. The opening paragraph made a promise — "here is who this is for, here is what it does." The rest of the README should pay that off quickly. Instead, it shifts into an exhaustive feature catalog. **Strategy, Product, Design, Code, Milestones, Corpus Management, Semantic Search, Review and Ship, Skills state tracking, Self-Updating, Auto Version Bumping** — eleven capability domains, each with a paragraph. This is not orientation for a new user. This is a product specification dressed as a README.

The structure problem: the README is doing too many jobs simultaneously. It is a feature catalog (What SweetClaude Does), a tutorial (Getting Started), a use case library (Key Use Cases), a command reference (All Commands — 80+ commands in tables), and a technical architecture explainer (How It Works). These should be separate pages. A README's job is to make someone decide to install. Every section past that decision point belongs in the docs.

---

**Nadia Okonkwo:**

Priscilla is right about the structure overload, and I want to name the specific cost: **it buries the social proof and emotional hook under reference material.**

The "Support" section at the very bottom — with Smushford the dog — is the most humanizing content in the entire document. It tells you this is a real person who built this tool because they needed it, who has a dog, who cares about what they're making. That is the content that makes developers want to contribute and cheer for the project. It is literally the last thing in the document.

The community-building content — "built by an enterprise CTO/CISO and serial entrepreneur, originally as his toolchain" — is in a one-sentence aside on line 12. The dog photo and Ko-fi are at the bottom. In between there are 80 commands in tables.

The emotional architecture of this README is inverted. Trust-building content is at the bottom; reference material is in the middle. For OSS community growth, this is backwards. Developers who might become contributors are not going to reach the bottom if the first 250 lines read like a man page.

---

**Marcus Löfgren:**

I want to note what the README does not say, because the absence matters for maintainability signal.

There is no **Project Status** badge or section. No "This project is actively maintained" or "This project is in early development." No commit frequency badge. No last-release date. No "we accept contributions" badge. These are 10-second reads that experienced OSS contributors use to filter whether to invest time. The absence of a status signal is read as ambiguous — which is, in this case, probably accurate. But ambiguity is not a trust-building state.

The README also does not answer: **how is SweetClaude versioned?** The README references a note about "git history rewritten on 2026-05-01," but there is no semantic version visible on the README. Is this 1.0? 0.x? The user docs files say "Version 1.1" but the README itself has no version. Versioning signals project maturity.

---

**Dmitri Volkov:**

I want to address the license and upstream dependencies section, which comes near the bottom.

**The license block is too short.** "GNU Affero General Public License v3.0 — free to use, modify, and distribute for any purpose. If you run SweetClaude as a network service..." — this is accurate but undersells the practical implication for most users. The practical implication is: **if you are a solo developer building a personal tool, AGPL costs you nothing.** Most developers see "AGPL" and assume restrictions. The README should pre-empt this: "AGPL means you can use SweetClaude freely for any personal or commercial project. The copyleft obligations only activate if you embed SweetClaude into a network service you offer to others."

The upstream dependencies table is honest and useful — it names Superpowers (MIT) and mcp-local-rag (MIT). But it says "SweetClaude orchestrates these plugins — it does not fork or modify them." This is a governance statement, not just a description, and it should be understood as such. The table should also note: what happens if these dependencies go unmaintained? Superpowers is MIT but also appears to be a solo project. The dependency risk is bilateral.

---

**Yuki Hashimoto:**

I'll make an empirical observation: **the README makes behavioral claims that are not hedged for model-version risk.**

Specifically, in the How It Works section: "TDD enforcement. During implementation, hooks physically block test file modifications." That is correct and deterministic. But immediately after: "Tests run automatically after every source edit" — also deterministic. But then: "Protocol Guardian. An optional enforcement layer that catches protocol drift mid-session." "Catches" implies reliability that is actually probabilistic. The README doesn't distinguish which behavioral properties are hook-enforced versus instruction-guided.

The README also says: "The behavioral regression suite runs 15 tests against the current model version." But it does not tell the reader: *at what version was this validated?* If I'm a prospective user, I want to know whether the behavioral contracts were validated on the model I'm running. Behavioral stability is one of SweetClaude's distinguishing claims, and the README does not give me the information I need to assess it.

**Structure proposal:** The README should include a "Verified on model" line — something like "15 behavioral contracts validated against claude-sonnet-4-6 as of 2026-05-01." Update it when re-validated. This turns the behavioral regression suite from a feature ("we have a test suite") into evidence ("these contracts held at this version").

---

**Proctor synthesis — Turn 4:**

**What works:**
- Opening paragraph: "not for everyone" + precise audience targeting is unusually effective
- Install simplicity is honest and low-friction
- CONTRIBUTING.md structure suggests a contributor funnel exists

**What doesn't:**
- README is doing 5 jobs simultaneously; should do 1 (make someone decide to install)
- Emotional/trust-building content buried at bottom; reference material dominates the above-the-fold experience
- No project status signals (badges, version, commit frequency)
- AGPL description undersells the permissive-for-most-users reality
- Behavioral claims in How It Works not hedged for model-version risk
- No "verified on model version X" anchor for behavioral claims

**Structural verdict:** The README's architecture is inverted for its audience-conversion job. It reads like comprehensive documentation for existing users, not a first-impression pitch for evaluators.

---

*Checkpoint: caucus_checkpoint_turn4.md written.*

---

---

# Turn 5: README — Specific Gaps, Misleading Claims, and Friction Points

**Proctor framing:** Turn 4 identified structural problems. This turn goes line-by-line. What specific text is incorrect, misleading, overly complex, or missing? We are looking for concrete edits, not structural opinions. Give me the specific problems and the specific fixes.

---

**Priscilla Tan:**

Three specific friction points with proposed fixes:

**1. The cost signal is buried.**

Current location: Prerequisites table, line 48. Required field shows "Claude Code" with no cost signal. 

A developer evaluating SweetClaude needs to know this requires an Anthropic subscription before they spend 10 minutes reading. The fix: add a one-line cost note to the opening "What is this?" section, not just the prerequisites table. Something like: "Requires [Claude Code](https://claude.ai/code) — Anthropic's terminal-based coding tool (paid subscription)."

**2. "Quick Try (No Install)" is misleading.**

Current text: "Want to try SweetClaude without installing? Load it as a plugin for a single session:" followed by `claude --plugin-dir /path/to/sweetclaude`.

This is not a quick try. It still requires cloning the repo, having Claude Code installed, and knowing what a plugin-dir is. The "quick try" label raises an expectation of zero friction. The actual experience is a developer install process. Either rename this section ("Try Without Global Install") or remove the "quick" framing.

**3. The "Things to Try First" section should be first, not third.**

Current position: After "Install" (which comes after Prerequisites). A developer who just landed on the README wants to know if this is worth their time before they look at install steps. The "Things to Try First" section — with its conversational prompts and low-stakes actions — is the right answer to "is this worth my time?" It should appear immediately after the two-paragraph opening, before Prerequisites and Install.

---

**Nadia Okonkwo:**

Specific gaps I want to name:

**1. No community links.**

The README has no Discord, no GitHub Discussions, no forum, nothing. A contributor reading the README does not know where to ask questions. The Contribute section says "open an issue or PR" — but without a link to an active discussion space, this invites feature requests to land in the issue tracker as discussion threads, which is an OSS anti-pattern.

Concrete fix: if no community space exists, create a GitHub Discussions space (free, zero setup) and add a "Questions and ideas → GitHub Discussions" link to the Contribute section. If there is an existing community space not listed, add it.

**2. The "Getting Started: Your First Session" section is inside a larger "Getting Started" section.**

The section titled "Getting Started" has four subsections: Prerequisites, Install, Quick Try, Things to Try First, Your First Session. A developer navigating via browser ToC sees "Getting Started" and then has to read through prerequisites before finding the first session guidance. The navigation architecture buries the activation path.

Concrete fix: make "Your First Session" the first sub-section under "Getting Started." Put prerequisites and install in a collapsible details block or push them to an INSTALL.md.

**3. The Contributing section is one paragraph with no contributor count.**

"Contributions welcome. SweetClaude is built by solo developers, for solo developers. If you have ideas, skills, or improvements — read CONTRIBUTING.md for where to start, then open an issue or PR."

This is accurate but thin. There is no contributor count badge, no "good first issue" count, no "we merged X PRs last month" signal. For an OSS contributor deciding whether to invest time, social proof of existing contribution activity matters. Even if the project is new, a badge showing "1 contributor, 3 open issues" gives more signal than a blank Contribute section.

---

**Marcus Löfgren:**

Specific text issues:

**1. "Built by an enterprise CTO/CISO and serial entrepreneur, originally as his toolchain."**

This is an interesting positioning line — it signals the tool comes from real-world use, not academic theory. But it also signals: one person. For a contributor evaluating bus factor, this is a yellow flag dressed in credentials. I would reframe it: "Built by an enterprise CTO/CISO and serial entrepreneur, originally as his own toolchain — and now looking for collaborators." The addition does not compromise the authority signal and changes the narrative from "solo tool" to "growing project."

**2. The "How It Works" section length.**

The How It Works section in the README is 1,100 words and covers state tracking, TDD enforcement, corpus management, semantic search, milestones, auto version bumping, self-updating, Protocol Guardian, improvement register, John Wick mode, and language agnosticism. This is not "How It Works" — this is a feature dump with explanatory prose.

"How It Works" should be a 3–4 paragraph summary of the architecture philosophy, with a link to the full how-it-works.md doc. The detailed feature explanations belong in the doc, not the README.

**3. The "Note for existing clones" banner is prominent and possibly permanent.**

The README currently has a banner: "Note for existing clones (2026-05-01): The git history was rewritten today..." This is a legitimate notice for today. It is noise for anyone reading this in six months. It should be time-boxed — either remove it after 30 days or convert it to a changelog entry.

---

**Dmitri Volkov:**

Two specific claims to address:

**1. "free to use, modify, and distribute for any purpose"**

This is the AGPL description in the License section. "For any purpose" is technically correct for personal use but technically incomplete for commercial network service use. The AGPL requires source disclosure for network services. The phrase "for any purpose" creates a false impression of MIT-like permissiveness.

Proposed rewrite: "Free to use, modify, and distribute. No license fees, no usage restrictions for personal or commercial tools. If you deploy SweetClaude as a network service offered to others, AGPL requires you to make your modified source available. Read [LICENSE](LICENSE) for the full terms."

This framing is: accurately AGPL, does not oversimplify, and pre-empts the most common misreading ("AGPL means I can't use this commercially").

**2. Superpowers listed as "Required" for full install**

The upstream dependencies table lists Superpowers as "Required — Full install." But the README elsewhere says "SweetClaude orchestrates Superpowers — it does not fork or modify them." This creates a question: is Superpowers required, or is it used when present? If a user can install SweetClaude without Superpowers and have a degraded but functional experience, the "Required" label is incorrect and will cause unnecessary install abandonment.

Concrete fix: change "Required" to "Required for code/TDD features" and add a row note explaining what is lost without it.

---

**Yuki Hashimoto:**

Two empirically-grounded issues:

**1. "Tests run automatically after every source edit"**

This statement, in the How It Works section, is a behavioral claim. Based on my reading of the architecture, this is a PostToolUse hook — deterministic. But the word "automatically" in this context implies unconditional reliability. The correct statement is: "Tests run automatically after every source edit via a PostToolUse hook — this is hook-enforced, not advisory." The hedge is not weakness — it is accuracy. Users who understand *why* it is reliable trust it more than users who are just told it is.

**2. The behavioral regression suite is described but not linked.**

The README mentions `/sweetclaude:behavioral-regression` runs "15 contracts." But there is no link to what those contracts are, no link to the SKILL.md file, no summary of what the contracts cover. A new user cannot evaluate whether the 15 contracts are meaningful or trivial. 

Concrete fix: add a sentence: "The 15 contracts cover phase dwelling, deference levels, adaptive language, improvement register capture, and more — see [behavioral-regression/SKILL.md](skills/behavioral-regression/SKILL.md) for the full list."

---

**Proctor synthesis — Turn 5:**

**Concrete issues identified:**

| Issue | Location | Proposed fix |
|---|---|---|
| Cost signal buried | Prerequisites table only | Add to opening section |
| "Quick Try" is misleading | Getting Started | Rename to "Try Without Global Install" |
| "Things to Try First" position | Third sub-section | Move to first sub-section after opening paragraphs |
| No community links | Contribute section | Add GitHub Discussions |
| Contributing section has no social proof | Contribute | Add contributor count badge or PR count |
| "Built by..." solo signal | Line 12 | Add "looking for collaborators" |
| How It Works in README is 1,100 words | Entire section | Cut to 3–4 paragraphs, link to full doc |
| "Note for existing clones" banner | Top of Getting Started | Time-box, remove after 30 days |
| "free to use for any purpose" | License section | Rewrite to clarify AGPL network service clause |
| Superpowers "Required" label | Dependencies table | Change to "Required for code/TDD features" |
| "Tests run automatically" unhedged | How It Works | Add "(hook-enforced)" qualifier |
| Behavioral regression suite not linked | Advanced commands table | Add link to SKILL.md |

---

*Checkpoint: caucus_checkpoint_turn5.md written.*

---

---

# Turn 6: README Final Verdict + Concrete Rewrite Recommendations

**Proctor framing:** Final turn. I want a verdict on the README as it stands — not all the individual issues, but the overall assessment. And I want a prioritized rewrite plan: if the maintainer has one day, what does he do? If he has one week, what else? What does he leave for later?

---

**Priscilla Tan:**

**Verdict:** The README is a B-minus product document masquerading as a B-plus user acquisition document. It succeeds at what it's not trying to do (comprehensive reference for existing users) and partially fails at what it is trying to do (convert evaluators into installers).

**One day plan:**
1. Move "Things to Try First" above Prerequisites and Install
2. Add cost signal to the opening two paragraphs
3. Cut "How It Works" to 200 words + link to full doc — this alone removes ~900 words of above-the-fold reference content
4. Remove or date-gate the existing-clone notice

These four changes reduce the README by about 40% and front-load the most conversion-effective content. A developer landing here will understand the tool, know the cost, and find a low-stakes try-it path in the first two screens.

**One week plan:**
5. Demo terminal recording embedded as GIF or linked video
6. "Things to Try First" rewritten as actual demos rather than "type this prompt" instructions — showing output, not just inputs
7. "Your First Session" section redesigned as a visual flow (not a list of commands)

**Later:**
8. Full structural reorganization into README (pitch/decision) + INSTALL.md (detailed install) + QUICKSTART.md (first session guide)

---

**Nadia Okonkwo:**

**Verdict:** The README is a project that trusts its audience too much. It assumes the reader will read all 350 lines carefully. Most will not. The content that would create contributors — the human story, the social proof, the community invitation — is all at the end. The content that loses evaluators — the 80+ command tables — is in the middle.

**One day plan:**
1. Add a GitHub Discussions link to the Contribute section
2. Add contributor count badge to the header (even if it shows "1 contributor" — honesty builds trust)
3. Move the Smushford / Ko-fi / Support section immediately below the opening "What is SweetClaude?" paragraphs — make the human story part of the pitch, not the postscript

**One week plan:**
4. Write walkthroughs.md — this is the single most-referenced missing document in the README
5. Move all 80+ command table content to a COMMANDS.md and replace in README with "→ Full command reference"
6. Add a "Project Status" section above the ToC: "Active development. Version X.Y. Last release: DATE. Contributions: welcome."

**Later:**
7. CODE_OF_CONDUCT.md and SUPPORT.md — community standards files that signal project maturity

---

**Marcus Löfgren:**

**Verdict:** This README will serve the project adequately until it gets attention. It will not survive a major attention spike without producing a high bounce rate and a lost cohort of potential contributors.

**One day plan:**
1. Add "looking for a technical co-maintainer" to the Contribute section — one paragraph, links to What Requires Full Framework Knowledge table
2. Add project status signals to the header: a shields.io badge for "built with ❤️ by [n] maintainers" even if n=1
3. Remove the "originally as his toolchain" framing or reframe it as described in T5 — the solo signal needs to be countered

**One week plan:**
4. Open a public "Co-maintainer wanted" GitHub issue with concrete scope
5. Add a ROADMAP.md — even a minimal one showing the 3–5 highest-priority things. This tells contributors what matters.

**Later:**
6. Formal governance document — especially if/when a second maintainer joins

---

**Dmitri Volkov:**

**Verdict:** The README is honest and technically sound, which is rarer than you'd think. The two specific legal/governance fixes (AGPL description, Superpowers label) are important but minor. The bigger gap is the missing dependency risk acknowledgment — not in the README specifically, but the README is the place to point to it once the policy document exists.

**One day plan:**
1. Fix the AGPL description (see T5 proposed rewrite)
2. Fix the Superpowers "Required" label to "Required for code/TDD features"
3. Add a "Platform Dependencies and Stability" note in the Upstream Dependencies section — even one sentence: "SweetClaude's plugin architecture depends on Claude Code's extension API. We track Anthropic's changelog for breaking changes."

**One week plan:**
4. Write the platform dependency policy document (see T3 recommendation)
5. Link it from the Upstream Dependencies section

**Later:**
6. Formal contributor license agreement if/when the project receives significant external contributions from organizations

---

**Yuki Hashimoto:**

**Verdict:** For an AI-tooling OSS project, the README is above average in its honesty about what is guaranteed and what is not. The enforcement tiers concept is visible in the docs, and the behavioral regression suite is mentioned. The gap is that none of this is surfaced prominently enough to be a differentiator for users who care about reliability.

**One day plan:**
1. Add "Verified on claude-sonnet-4-6 as of 2026-05-01" to the behavioral regression suite entry in the Advanced commands table
2. Link the behavioral regression SKILL.md from the same entry
3. In the How It Works section, distinguish explicitly between hook-enforced and instruction-guided properties with a single parenthetical: "TDD enforcement hooks are deterministic (hook-enforced); Protocol Guardian behavioral properties are instruction-guided and model-version sensitive."

**One week plan:**
4. Publish a "Current behavioral contract status" summary in CHANGELOG.md or a STATUS.md — which contracts pass on which model versions, updated each model release
5. This becomes the trust infrastructure I described in T2 — published model-version-tagged compliance reports

**Later:**
6. Automated CI behavioral regression integration — the multi-week engineering project, but the highest long-term differentiator

---

**Proctor synthesis — Turn 6:**

**Final README verdict:**

The README succeeds at its hardest job — communicating a precise audience and a clear value proposition — but fails at several execution details that matter for acquisition and community building. It is about 40% too long, buries its most trustworthy content, and is missing basic OSS health signals.

**Prioritized rewrite plan (consensus across panelists):**

**One day (4–6 hours):**
1. Move "Things to Try First" above Prerequisites/Install (Priscilla)
2. Add Anthropic cost signal to the opening section (Priscilla)
3. Cut How It Works in README to 200 words + link to full doc (Marcus/Priscilla)
4. Fix AGPL description — clarify personal/commercial vs. network service use (Dmitri)
5. Fix Superpowers "Required" → "Required for code/TDD features" (Dmitri)
6. Add "looking for technical co-maintainer" paragraph to Contribute section (Marcus)
7. Add "Verified on [model version] as of [date]" to behavioral regression entry (Yuki)
8. Remove or date-gate the existing-clone notice (Marcus)

**One week:**
9. Write walkthroughs.md — the single most-cited missing document (Nadia)
10. Move 80+ command tables to COMMANDS.md; replace in README with a link (Nadia)
11. Add project status signals to header (Marcus)
12. Add GitHub Discussions link to Contribute section (Nadia)
13. Demo terminal recording (Priscilla)
14. Write platform dependency policy document (Dmitri)
15. Publish behavioral contract status summary per model version (Yuki)

**Later (structural work):**
16. Full README reorganization: README (pitch) + INSTALL.md + QUICKSTART.md
17. ROADMAP.md
18. CODE_OF_CONDUCT.md, SUPPORT.md
19. Automated behavioral regression CI integration
20. Formal governance document

---

---

## Final Synthesis

### Position Trajectory

| Panelist | T1–T3 Primary Focus | T4–T6 Primary Focus | Shift? |
|---|---|---|---|
| Priscilla | TTFV, acquisition friction, demo gap | README cognitive load, Things to Try First buried | Consistent — friction obsession |
| Nadia | Missing community infrastructure | Emotional content buried, no community links | Consistent — community building focus |
| Marcus | Bus factor, co-maintainer gap | Solo signal, no project status | Consistent — sustainability |
| Dmitri | Platform dependency risk | AGPL description, Superpowers label | Consistent — governance/license |
| Yuki | Behavioral regression automation | Behavioral claims unanchored to model version | Consistent — stability/empirics |

No major position reversals. The personas remained true to their biases throughout — which is evidence of genuine disagreement rather than convergence theater.

### Consensus Findings

1. **The opening paragraph is strong.** Selective trust signal, precise audience. Leave it alone.
2. **The bus factor is the existential risk.** All panelists named it or touched it. It is not a documentation problem — it requires active outreach.
3. **Behavioral regression testing is genuinely distinctive.** No other panelist had seen this in an AI-tooling OSS project. The failure is in not surfacing it as a differentiator in the README.
4. **The README does 5 jobs and should do 1.** This is the structural diagnosis the whole committee agreed on by Turn 6.
5. **The documentation gaps (walkthroughs.md etc.) are an acquisition risk, not a quality problem.** The project is legitimately good; broken links make it look unfinished.

### Unresolved Disagreements

**Sequencing: documentation vs. co-maintainer vs. demo** — Marcus and Priscilla held a genuine disagreement throughout about whether to fix sustainability (co-maintainer) or acquisition (demo) first. The proctor called a sequenced view as the majority position, but Marcus's underlying argument — that a project with no second maintainer is structurally fragile regardless of how many users it acquires — was not defeated, only deferred.

**Platform dependency risk: accepted tradeoff or active mitigation required?** — Dmitri argued for active mitigation (policy document, contingency plan). The rest of the committee accepted the risk as a known constraint similar to VSCode extensions. Dmitri's minority position: "VSCode doesn't hold behavioral contracts. The Anthropic dependency risk is qualitatively different because behavior is part of what you're shipping."

### Prioritized Recommendations (Committee-ranked)

| Rank | Recommendation | Champion | Effort |
|---|---|---|---|
| 1 | Fill 5 broken documentation links | Nadia | 1 week |
| 2 | Launch co-maintainer search issue | Marcus | 30 min |
| 3 | Restructure README: move Things to Try First, cut How It Works | Priscilla | Half day |
| 4 | Add cost signal to opening section | Priscilla | 15 min |
| 5 | Fix AGPL description and Superpowers label | Dmitri | 1 hour |
| 6 | Add "Verified on model X as of date" to behavioral regression | Yuki | 15 min |
| 7 | Demo terminal recording | Priscilla | 1 day |
| 8 | Add GitHub Discussions + community links | Nadia | 30 min |
| 9 | Write platform dependency policy | Dmitri | 1 day |
| 10 | Publish behavioral contract status per model version | Yuki | 2 days |
| 11 | Automate behavioral regression CI | Yuki | Multi-week |

### Minority Reports

**Marcus Löfgren (on sequencing):** "Every action the committee prioritized — documentation, demos, README improvements — attracts users. Users without a second maintainer create a crisis in 18–24 months. The co-maintainer search is the only action that changes the project's structural trajectory, not just its growth trajectory. It is ranked second on the list, but it should be treated as a parallel track, not a sequential one. Run the co-maintainer search while doing everything else. Do not wait."

**Dmitri Volkov (on platform dependency):** "The committee treated Anthropic platform risk as a known tradeoff, the same way VSCode extension developers treat Microsoft. I do not accept this framing. VSCode is agnostic about what extensions do. Claude Code constrains the behavior the extensions can express, and that constraint is what SweetClaude is selling. If Anthropic changes the rules for what CLAUDE.md can contain, or what PostToolUse hooks can do, SweetClaude's core value proposition is at risk. This is not analogous to VSCode. The project should have a written answer to: 'what do we do if Anthropic changes this?' Even if the answer is 'we adapt,' it should be written."

---

*All checkpoints written. Caucus complete.*
