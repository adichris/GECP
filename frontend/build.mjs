import { mkdirSync, copyFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
mkdirSync('static/css', { recursive: true });
mkdirSync('static/js', { recursive: true });
mkdirSync('static/fonts', { recursive: true });
execFileSync(process.execPath, ['node_modules/@tailwindcss/cli/dist/index.mjs', '-i', 'frontend/app.css', '-o', 'static/css/app.css', '--minify'], { stdio: 'inherit' });
copyFileSync('node_modules/htmx.org/dist/htmx.min.js', 'static/js/htmx.min.js');
copyFileSync('node_modules/alpinejs/dist/cdn.min.js', 'static/js/alpine.min.js');
// Self-hosted variable fonts (Latin + Latin Extended); no browser CDN dependencies.
for (const [pkg, prefix] of [['inter', 'inter'], ['plus-jakarta-sans', 'plus-jakarta-sans']]) {
  for (const subset of ['latin', 'latin-ext']) {
    copyFileSync(`node_modules/@fontsource-variable/${pkg}/files/${prefix}-${subset}-wght-normal.woff2`, `static/fonts/${prefix}-${subset}.woff2`);
  }
}
