// Render every snippet as a VS Code window, using the same theme VS Code uses.
// Shiki reads the TextMate grammar and the dark-plus theme, so the colours match.

import { readFileSync, writeFileSync } from 'node:fs';
import { codeToHtml } from 'shiki';

const [, , input, output] = process.argv;
const rows = JSON.parse(readFileSync(input, 'utf8'));

const ICON = {
  python: 'py',
  tsx: 'ts',
};

const escape = (text) =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const parts = [];
for (const row of rows) {
  const html = await codeToHtml(row.code, {
    lang: row.lang,
    theme: 'dark-plus',
  });
  const breadcrumb = row.file.split('/').join('  ›  ');
  const base = row.file.split('/').pop();
  const language = row.lang === 'python' ? 'Python' : 'TypeScript React';
  const partNote = row.parts > 1 ? ` · part ${row.part} of ${row.parts}` : '';
  const body = row.offset
    ? html.replace('<pre class="shiki', `<pre style="counter-reset: line ${row.offset}" class="shiki`)
    : html;
  parts.push(`
<section class="snippet" id="${row.key}">
  <div class="titlebar">
    <div class="tab">
      <span class="chip ${ICON[row.lang]}">${ICON[row.lang]}</span>
      <span class="tabname">${escape(base)}</span>
      <span class="tabclose">✕</span>
    </div>
    <div class="wintitle">${escape(row.file)} — CSIT314</div>
  </div>
  <div class="breadcrumb">${escape(breadcrumb)}  ›  ${escape(row.name)}${partNote}</div>
  ${body}
  <div class="statusbar">
    <span class="branch">⑂ main</span>
    <span class="right">${language} · UTF-8 · LF · lines ${row.start}–${row.end}${partNote}</span>
  </div>
</section>`);
}

const page = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: #1e1e1e;
    font-family: "Segoe UI", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .snippet {
    width: max-content;
    min-width: 760px;
    background: #1e1e1e;
    color: #d4d4d4;
    margin: 0;
    overflow: visible;
    padding-bottom: 6px;
  }
  .titlebar {
    display: flex;
    align-items: center;
    gap: 18px;
    background: #3c3c3c;
    height: 34px;
    padding: 0 12px 0 0;
  }
  .tab {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #1e1e1e;
    height: 34px;
    padding: 0 12px;
    font-size: 12px;
    color: #ffffff;
    border-top: 1px solid #007acc;
  }
  .chip {
    display: inline-block;
    font: 700 9px/14px "Segoe UI", sans-serif;
    text-align: center;
    width: 15px;
    height: 14px;
    border-radius: 2px;
    color: #ffffff;
  }
  .chip.py { background: #3572a5; }
  .chip.ts { background: #2b7489; }
  .tabclose { color: #9d9d9d; margin-left: 6px; font-size: 10px; }
  .wintitle { color: #9d9d9d; font-size: 12px; }
  .breadcrumb {
    background: #1e1e1e;
    color: #a9a9a9;
    font: 12px/28px "Segoe UI", sans-serif;
    padding: 0 18px;
    border-bottom: 1px solid #2b2b2b;
  }
  .shiki {
    counter-reset: line;
    margin: 0;
    padding: 8px 18px 10px 0;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 12.5px;
    line-height: 19px;
    tab-size: 4;
    white-space: normal;
    background: #1e1e1e !important;
  }
  .shiki .line { display: block; padding-left: 4px; white-space: pre; }
  .shiki .line::before {
    counter-increment: line;
    content: counter(line);
    display: inline-block;
    width: 3.4ch;
    text-align: right;
    margin-right: 1.6ch;
    color: #858585;
    user-select: none;
  }
  .statusbar {
    display: flex;
    justify-content: space-between;
    background: #007acc;
    color: #ffffff;
    font: 11px/22px "Segoe UI", sans-serif;
    padding: 0 14px;
  }
  .statusbar .branch { opacity: 0.95; }
  .statusbar .right { opacity: 0.95; }
</style>
</head>
<body>
${parts.join('\n')}
</body>
</html>`;

writeFileSync(output, page, 'utf8');
console.log('wrote', output, rows.length, 'snippets');
