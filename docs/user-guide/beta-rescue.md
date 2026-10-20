# SweetClaude 4.x Beta Rescue

Use this page if you installed the 4.x beta and SweetClaude is stuck, noisy, or reporting confusing update, doctor, migrate, or repair advice. The beta channel is retired, so the fix is a one-time switch to stable.

The safe path is:

1. Switch the Claude Code plugin to the stable marketplace.
2. Restart Claude Code.
3. Run SweetClaude's framework update only after the new plugin has loaded.
4. Use recovery for project state problems.

Do not try to fix a beta install by running project migration commands first.

---

## Step 1: Switch To Stable

Inside Claude Code, check which plugin key is installed:

```
/plugin list
```

If you see `sweetclaude@sweetclaude-beta` (or the legacy beta key `sweetclaude@sweetclaude`), run these in order so you are never double-installed:

```
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
/plugin marketplace remove sweetclaude-beta
```

---

## Step 2: Restart Claude Code

Claude Code loads plugin skills at session start. After the switch, restart Claude Code before running any SweetClaude commands.

---

## Step 3: Repair SweetClaude Metadata

After restart, run:

```
/sweetclaude:configure update
```

If the project needs repair, also run:

```
/sweetclaude:configure doctor
```

Update repairs stale plugin metadata and does not migrate project files inline. If it reports project drift, stop there and use doctor or recover. Do not run migration commands directly.

---

## Step 4: Recover A Stuck Project

If a project was left in a bad migration, doctor, update, or repair state:

```
/sweetclaude:configure recover
```

Recovery diagnoses first, shows a plan, snapshots before mutation, and asks before execution. If recovery reports a safe plan, continue from the same command flow. Recovery snapshots affected SweetClaude state and product artifacts before changing anything, verifies the result, and reports rollback instructions.

---

## Staying On 3.x

To stay on the 3.x line instead of moving to stable 5.x:

```
/plugin marketplace add carson-sweet/sweetclaude@stable-3.x
/plugin install sweetclaude@sweetclaude-legacy
```

---

## What Not To Do

Do not install old 4.x beta tags on active projects.

Do not run `/sweetclaude:configure migrate`, `/sweetclaude:configure doctor` autofixes, or `/sweetclaude:configure fix-sweetclaude` as the first response to a broken beta install. Switch to stable, restart Claude Code, then use `/sweetclaude:configure update` or `/sweetclaude:configure recover`.

Do not mix stable and beta marketplaces for the same install. Use the exact plugin key shown by `/plugin list`.
