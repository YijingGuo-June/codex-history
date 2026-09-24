import {mkdir, copyFile, cp} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dest = path.join(root, 'plugins/codex-history/assets/vendor');
await mkdir(dest, {recursive: true});
for (const [from, to] of [
  ['marked/lib/marked.umd.js', 'marked.js'], ['marked/LICENSE', 'LICENSE-marked.md'],
  ['dompurify/dist/purify.min.js', 'purify.js'], ['dompurify/LICENSE', 'LICENSE-dompurify'],
  ['katex/dist/katex.min.js', 'katex.js'], ['katex/dist/katex.min.css', 'katex.css'], ['katex/LICENSE', 'LICENSE-katex'],
  ['prismjs/prism.js', 'prism.js'], ['prismjs/LICENSE', 'LICENSE-prism'],
  ...['python', 'bash', 'json', 'rust', 'typescript'].map(lang => [`prismjs/components/prism-${lang}.min.js`, `prism-${lang}.js`]),
]) await copyFile(path.join(root, 'node_modules', from), path.join(dest, to));
await cp(path.join(root, 'node_modules/katex/dist/fonts'), path.join(dest, 'fonts'), {recursive: true});
console.log('Vendored pinned Markdown, math, sanitization and syntax libraries. No runtime CDN.');
