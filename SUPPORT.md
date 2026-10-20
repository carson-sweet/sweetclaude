# Support

## Questions and ideas

Use [GitHub Discussions](https://github.com/carson-sweet/sweetclaude/discussions). Questions in Issues get closed and redirected here.

## Bugs

[Open a GitHub issue](https://github.com/carson-sweet/sweetclaude/issues). Include: what you ran, what you expected, what happened instead. If there is a relevant state file (`.sweetclaude/state/sweetclaude.yaml`), include its contents. If the problem involves update, migration, repair, or recovery, also include the visible output from `/sweetclaude:doctor` or `/sweetclaude:recover`; do not include recovery snapshot archives.

## Model compatibility

If behavior changed after a Claude model upgrade, score a session transcript with `python3 scripts/behavioral_judge.py score --transcript <session.jsonl> --contract CONTRACT-NN` to identify which contracts failed. Include the output in your issue report. This is the fastest path to a fix.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) first. Good first contributions are the product and design skills — isolated state footprint, no hook system knowledge required.

Looking for a co-maintainer for the core framework — see [issue #7](https://github.com/carson-sweet/sweetclaude/issues/7).

## Security

Do not open a public issue for security vulnerabilities. Email cs@carsonsweet.com with a description and reproduction steps. Response within 48 hours.
