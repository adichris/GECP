import { mkdirSync, copyFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
mkdirSync('static/css', { recursive: true });
mkdirSync('static/js', { recursive: true });
execFileSync(process.execPath, ['node_modules/@tailwindcss/cli/dist/index.mjs', '-i', 'frontend/app.css', '-o', 'static/css/app.css', '--minify'], { stdio: 'inherit' });
copyFileSync('node_modules/htmx.org/dist/htmx.min.js', 'static/js/htmx.min.js');
copyFileSync('node_modules/alpinejs/dist/cdn.min.js', 'static/js/alpine.min.js');
