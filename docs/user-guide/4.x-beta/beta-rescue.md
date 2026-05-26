# SweetClaude 4.x Beta Rescue

Use this page if you installed the 4.x beta and SweetClaude is stuck, noisy, or
reporting confusing update, doctor, migrate, or repair advice.

The safe path is:

1. Update the Claude Code plugin package.
2. Restart Claude Code.
3. Run SweetClaude's framework update only after the new plugin has loaded.
4. Use recovery for project state problems.

Do not try to fix a beta install by running project migration commands first.

---

## Step 1: Check The Installed Plugin Key

Inside Claude Code:

```
/plugin list
```

If you see:

```
sweetclaude@sweetclaude-beta
```

update with:

```
/plugin update sweetclaude@sweetclaude-beta
```

If you see the legacy beta key:

```
sweetclaude@sweetclaude
```

update that exact key:

```
/plugin update sweetclaude@sweetclaude
```

This should move the beta install to the current `4.1.12-beta` or newer release.

---

## Step 2: Restart Claude Code

Claude Code loads plugin skills at session start. After the plugin update,
restart Claude Code before running any SweetClaude commands.

---

## Step 3: Repair SweetClaude Metadata

After restart, run:

```
/sweetclaude:update
```

The 4.1.9 and later beta update path preserves the stable/beta channel boundary, ignores
wrong-branch local developer repos, repairs stale plugin metadata, and does not
migrate project files inline.

If the update reports project drift, stop there and use doctor or recover. Do
not run migration commands directly.

---

## Step 4: Recover A Stuck Project

If a project was left in a bad migration, doctor, update, or repair state:

```
/sweetclaude:recover
```

Recovery diagnoses first, shows a plan, snapshots before mutation, and asks
before execution. If recovery reports a safe plan, continue from the same
command flow. Recovery snapshots affected SweetClaude state and product
artifacts before changing anything, verifies the result, and reports rollback
instructions.

---

## Stable Users

Stable users should stay on the 3.x stable channel:

```
/plugin marketplace add carson-sweet/sweetclaude@stable-3.x
/plugin install sweetclaude@sweetclaude-stable
```

Stable updates use:

```
/plugin update sweetclaude@sweetclaude-stable
```

Stable installs should not update to the 4.x beta unless you intentionally add
and install the beta marketplace.

---

## What Not To Do

Do not install old 4.x beta tags on active projects.

Do not run `/sweetclaude:migrate`, `/sweetclaude:doctor` autofixes, or
`/sweetclaude:fix-sweetclaude` as the first response to a broken beta install.
First update the plugin package, restart Claude Code, then use
`/sweetclaude:update` or `/sweetclaude:recover`.

Do not mix stable and beta marketplaces for the same install. Use the exact
plugin key shown by `/plugin list`.
