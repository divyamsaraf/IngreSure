/**
 * Runs `next build` and filters out the baseline-browser-mapping "two months old"
 * warning from stderr. All other output and the exit code are preserved.
 * Cross-platform (Node); does not change build behavior.
 */
const { spawn } = require('child_process');
const path = require('path');

const BASELINE_WARNING = '[baseline-browser-mapping]';
const BASELINE_WARNING_SUB = 'two months old';

function shouldFilterLine(line) {
  return (
    line.includes(BASELINE_WARNING) && line.includes(BASELINE_WARNING_SUB)
  );
}

const cwd = path.join(__dirname, '..');
const child = spawn('npx', ['next', 'build'], {
  cwd,
  stdio: ['inherit', 'pipe', 'pipe'],
  env: process.env,
  shell: true,
});

child.stdout.pipe(process.stdout);
child.stderr.on('data', (chunk) => {
  const str = chunk.toString();
  const lines = str.split('\n');
  const endsWithNewline = str.endsWith('\n');
  lines.forEach((line, i) => {
    if (shouldFilterLine(line)) return;
    const isLast = i === lines.length - 1;
    process.stderr.write(line + (isLast && !endsWithNewline ? '' : '\n'));
  });
});

child.on('close', (code) => {
  process.exit(code ?? 0);
});
