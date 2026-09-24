# Contributing

Thanks for helping make long Codex conversations easier to read.

## Run the project

Python 3.9+ is enough for the runtime. From the repository root:

```sh
python3 plugins/codex-history/scripts/history.py open --demo
python3 -m unittest discover -s tests -v
node --check plugins/codex-history/assets/viewer.js
```

For live UI development, use `open --live --demo`. The synthetic demo never reads your Codex sessions. Runtime libraries and fonts are committed under `plugins/codex-history/assets/vendor/`.

## Where things live

| Path | Purpose |
| --- | --- |
| `plugins/codex-history/scripts/history_reader.py` | Read-only SQLite and JSONL ingestion |
| `plugins/codex-history/scripts/history.py` | Launcher, local server, synthetic demo |
| `plugins/codex-history/scripts/standalone.py` | Self-contained HTML generation |
| `plugins/codex-history/assets/viewer.*` | Reader UI, navigation, rendering |
| `plugins/codex-history/skills/history/SKILL.md` | Instructions executed by Codex |
| `tests/test_history.py` | Standard-library runtime tests |

## Before a pull request

- Describe the user-visible problem and the behavior your change enables.
- Include a focused regression test for parser or security changes.
- For UI changes, include screenshots made with synthetic sample data.
- Keep the English and Chinese README consistent when changing behavior or installation.
- Keep the runtime free of pip/npm setup requirements. Do not add remote scripts, analytics, or automatic external-image loading.

Never commit real conversations, tokens, configuration files, SQLite databases, or private HTML exports. For compatibility reports, provide a small **synthetic** record with the same structure, the Codex version, operating system, and an error message with private paths removed.

## Updating rendering dependencies

Update `package.json` and its lockfile deliberately, then run:

```sh
npm ci --ignore-scripts
npm run vendor
python3 -m unittest discover -s tests -v
```

Keep vendor licenses and `THIRD_PARTY_NOTICES.md` accurate. Regenerate `demo.html` using `DemoStore` and `standalone.build_html` after changing frontend assets. Screenshots in `docs/images/` must represent the actual reader, not a mockup.

By contributing, you agree that your contributions are licensed under the project's MIT license.
