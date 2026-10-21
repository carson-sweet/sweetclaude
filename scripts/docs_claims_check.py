#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = r"\$\{CLAUDE_PLUGIN_ROOT\}/"
PATH_PREFIXES = (
    "docs/", "skills/", "skill-library/", "scripts/", "hooks/", "agents/",
    "commands/", "templates/", "tests/", "rules/", "schemas/",
)
PREFIX = "sweetclaude" + ":"
SLASH_RE = re.compile(r"(?<![\w/:.])/sweetclaude" + r":([\w-]+)(?:[ \t]+([\w-]+))?")
SCRIPT_RE = re.compile(r"python3?\s+(?:" + PLUGIN_ROOT + r")?(scripts/[^\s`'\")]+\.py)([^`\n]*)")
SPAN_RE = re.compile(r"`([^`\s]+)`")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
CHOICES_RE = re.compile(r"\{([\w.-]+(?:,[\w.-]+)*)\}")
ARG_STOP = re.compile(r"\s*(?:\||;|&&|>|<|#|\\$)")

MARKER_RE = re.compile(r"<!--\s*docs-claims:\s*ignore\s+(\w+):(\S+?)\s*-->")

_help_cache = {}


def script_help(script, sub=None):
    key = (str(script), sub)
    if key not in _help_cache:
        cmd = [sys.executable, str(script)] + ([sub] if sub else []) + ["--help"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if res.returncode != 0:
                _help_cache[key] = (None, f"--help exited {res.returncode}")
            else:
                _help_cache[key] = (res.stdout + res.stderr, None)
        except Exception as exc:
            _help_cache[key] = (None, f"--help failed: {type(exc).__name__}")
    return _help_cache[key]


def finding(path, line, kind, claim, reason):
    return {"path": path, "line": line, "kind": kind, "claim": claim, "reason": reason}


def check_slash(root, rel, lineno, line):
    out = []
    for m in SLASH_RE.finditer(line):
        name, nxt = m.group(1), m.group(2)
        if (root / "skills" / name / "SKILL.md").is_file():
            continue
        category = root / "skill-library" / name
        if category.is_dir():
            if nxt is None or (category / nxt / "SKILL.md").is_file():
                continue
            out.append(finding(rel, lineno, "slash", f"/{PREFIX}{name} {nxt}",
                               f"no skill-library/{name}/{nxt}/SKILL.md"))
            continue
        claim = m.group(0).split()[0] if nxt is None else f"/{PREFIX}{name}"
        out.append(finding(rel, lineno, "slash", claim,
                           f"no skills/{name}/SKILL.md or skill-library/{name}/"))
    return out


def arg_tokens(rest):
    stop = ARG_STOP.search(rest)
    if stop:
        rest = rest[:stop.start()]
    return rest.split()


def check_scripts(root, rel, lineno, line):
    out = []
    for m in SCRIPT_RE.finditer(line):
        script_rel = m.group(1)
        script = root / script_rel
        if not script.is_file():
            out.append(finding(rel, lineno, "script", script_rel, f"{script_rel} does not exist"))
            continue
        tokens = arg_tokens(m.group(2))
        flags = [t.split("=")[0] for t in tokens if re.match(r"^--[A-Za-z][\w-]*", t)]
        first = tokens[0] if tokens else None
        if not flags and not first:
            continue
        text, err = script_help(script)
        if err:
            out.append(finding(rel, lineno, "flag", script_rel, err))
            continue
        sub = None
        if first and not first.startswith(("-", "$", "<", "{", "'", '"', "[")):
            choices = CHOICES_RE.search(text)
            if choices:
                names = choices.group(1).split(",")
                if first in names:
                    sub = first
                else:
                    out.append(finding(rel, lineno, "flag", f"{script_rel} {first}",
                                       f"unknown subcommand {first}; expected one of {', '.join(names)}"))
        known = text
        if sub:
            sub_text, sub_err = script_help(script, sub)
            if sub_text:
                known = text + "\n" + sub_text
        for flag in flags:
            if not re.search(r"(?<![\w-])" + re.escape(flag) + r"(?![\w-])", known):
                out.append(finding(rel, lineno, "flag", f"{script_rel} {flag}",
                                   f"{flag} not in --help output"))
    return out


def check_paths(root, rel, lineno, line):
    out = []
    for m in SPAN_RE.finditer(line):
        span = re.sub("^" + PLUGIN_ROOT, "", m.group(1)).rstrip(".,;:")
        if not span.startswith(PATH_PREFIXES) or re.search(r"[*<>{}$|]", span):
            continue
        if not (root / span).exists():
            out.append(finding(rel, lineno, "path", span, f"{span} does not exist"))
    return out


def check_links(root, base, rel, lineno, line):
    out = []
    for m in LINK_RE.finditer(line):
        target = m.group(1)
        if target.startswith("#") or SCHEME_RE.match(target) or re.search(r"[<>{}$]", target):
            continue
        file_part = target.split("#")[0].split("?")[0]
        if not file_part:
            continue
        if not (base / file_part).exists():
            out.append(finding(rel, lineno, "link", target, f"{file_part} does not exist relative to {base.relative_to(root) if base != root else '.'}"))
    return out


def marker_matches(marker, f):
    _, kind, claim, _ = marker
    return f["kind"] == kind and (f["claim"] == claim or f["claim"].endswith(" " + claim))


def check_file(root, path):
    rel = path.relative_to(root).as_posix()
    findings = []
    in_fence = False
    lines = path.read_text().splitlines()
    markers = [
        [lineno, m.group(1), m.group(2), False]
        for lineno, line in enumerate(lines, 1)
        for m in MARKER_RE.finditer(line)
    ]
    for lineno, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        line = MARKER_RE.sub("", line)
        found = check_slash(root, rel, lineno, line)
        found += check_scripts(root, rel, lineno, line)
        if not in_fence:
            found += check_paths(root, rel, lineno, line)
            found += check_links(root, path.parent, rel, lineno, line)
        for f in found:
            hit = [m for m in markers if m[0] in (lineno, lineno - 1) and marker_matches(m, f)]
            for m in hit:
                m[3] = True
            if not hit:
                findings.append(f)
    for lineno, kind, claim, used in markers:
        if not used:
            findings.append(finding(rel, lineno, "marker", claim,
                                    f"no {kind} claim {claim} on this line or the next"))
    return findings


def main():
    parser = argparse.ArgumentParser(description="Verify references in user-facing docs resolve")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]), help="repository root")
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    parser.add_argument("paths", nargs="*", help="files to scan, relative to root")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if args.paths:
        files = [(root / p).resolve() for p in args.paths]
    else:
        files = []
        if (root / "README.md").is_file():
            files.append(root / "README.md")
        files += sorted((root / "docs" / "user-guide").rglob("*.md"))
    findings = []
    for f in files:
        findings += check_file(root, f)
    if args.json:
        print(json.dumps(findings, indent=2))
    elif findings:
        for f in findings:
            print(f"{f['path']}:{f['line']}: {f['kind']}: {f['claim']} - {f['reason']}")
    else:
        print("all documentation claims resolve")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
