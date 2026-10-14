// Compile every inline script in both entry points without executing it.
import { readFile } from 'node:fs/promises';
import { Script } from 'node:vm';
for (const name of ['index.html', 'editor.html']) {
  const html = await readFile(new URL('../ghiro_preventivi/' + name, import.meta.url), 'utf8');
  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
  if (!scripts.length) throw new Error('No inline script in ' + name);
  scripts.forEach((match, i) => new Script(match[1], { filename: name + ':script-' + (i + 1) }));
  console.log(name + ': syntax OK');
}
