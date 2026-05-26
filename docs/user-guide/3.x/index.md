# SweetClaude 3.x Stable User Guide

Use this track if you installed SweetClaude from `stable-3.x` or your plugin list shows `sweetclaude@sweetclaude-stable`.

3.x is the stable channel. It is the recommended channel for active project work unless you are intentionally testing 4.x beta behavior.

## Install

```text
/plugin marketplace add carson-sweet/sweetclaude@stable-3.x
/plugin install sweetclaude@sweetclaude-stable
```

Then run:

```text
/sweetclaude:help
```

## Update

Update the Claude Code plugin package first:

```text
/plugin update sweetclaude@sweetclaude-stable
```

Restart Claude Code so the new plugin package is loaded. Then run this inside a SweetClaude project if framework files need syncing:

```text
/sweetclaude:update
```

`/sweetclaude:update` is for syncing SweetClaude framework files inside the stable channel. It does not move a stable 3.x install onto 4.x beta. To try 4.x beta, add and install the beta marketplace explicitly.

## Project State

3.x projects should follow the 3.x commands and storage model supplied by the stable plugin. The shared conceptual guide still applies: phases, workflow shapes, TDD levels, corpus management, and deference levels are the same product ideas. Operational storage and migration docs are version-specific.

## Start Here

- [Getting Started](../getting-started.md)
- [Quick Start](../quickstart.md)
- [State and Memory](../state-and-memory.md)
- [Skills Reference](../skills-reference.md)
- [Install and Update](../install.md)
