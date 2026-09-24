# Bundled rendering libraries

All runtime assets are under `plugins/codex-history/assets/vendor/`. The offline demo embeds copies of these assets; the original license notices are retained here and in that directory.

| Library | Version | License | Upstream |
| --- | --- | --- | --- |
| Marked | 18.0.14 | MIT | https://github.com/markedjs/marked |
| DOMPurify | 3.4.16 | Apache-2.0 OR MPL-2.0 | https://github.com/cure53/DOMPurify |
| KaTeX, including fonts | 0.18.9 | MIT | https://github.com/KaTeX/KaTeX |
| Prism | 1.30.0 | MIT | https://github.com/PrismJS/prism |

Pinned development sources and integrity hashes are in `package-lock.json`. The build script copies the license files alongside the vendored libraries. No rendering assets are fetched from these sites at runtime.
