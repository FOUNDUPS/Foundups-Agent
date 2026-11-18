import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const url = process.argv[2] ?? 'http://[::1]:3000/';
const selector = process.argv[3] ?? 'body';
const output = path.resolve(process.argv[4] ?? 'audit/screenshots/section.png');
const port = 9338;
const profile = path.resolve('audit', `chrome-profile-cdp-${Date.now()}`);

await mkdir(path.dirname(output), { recursive: true });

const chrome = spawn(chromePath, [
  '--headless=new',
  '--disable-gpu',
  '--hide-scrollbars',
  '--no-first-run',
  '--disable-background-networking',
  `--remote-debugging-port=${port}`,
  '--remote-debugging-address=127.0.0.1',
  `--user-data-dir=${profile}`,
  url,
], { stdio: 'ignore', windowsHide: true });

async function waitForPage() {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      const pages = await fetch(`http://127.0.0.1:${port}/json/list`).then((response) => response.json());
      const page = pages.find((candidate) => candidate.type === 'page');
      if (page?.webSocketDebuggerUrl) return page;
    } catch {
      // Chrome is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error('Chrome DevTools page did not become ready.');
}

const page = await waitForPage();
const socket = new WebSocket(page.webSocketDebuggerUrl);
const pending = new Map();
let nextId = 0;

socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data);
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolve(message.result);
});

await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true });
  socket.addEventListener('error', reject, { once: true });
});

function send(method, params = {}) {
  const id = ++nextId;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

try {
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 1,
    mobile: true,
  });
  await new Promise((resolve) => setTimeout(resolve, 1200));

  await send('Runtime.evaluate', {
    expression: 'document.fonts?.ready ?? Promise.resolve()',
    awaitPromise: true,
  });
  const requestedLanguage = new URL(url).searchParams.get('lang');
  if (requestedLanguage === 'en' || requestedLanguage === 'pt' || requestedLanguage === 'ja') {
    const label = requestedLanguage === 'en' ? 'English' : requestedLanguage === 'pt' ? 'Português' : '日本語';
    await send('Runtime.evaluate', {
      expression: `document.querySelector(${JSON.stringify(`button[aria-label="${label}"]`)})?.click()`,
    });
    await new Promise((resolve) => setTimeout(resolve, 400));
  }

  let scrollResult = await send('Runtime.evaluate', {
    expression: `(() => { const target = document.querySelector(${JSON.stringify(selector)}); if (!target) return false; target.scrollIntoView({ block: 'start' }); return true; })()`,
    returnByValue: true,
  });
  if (!scrollResult.result.value) throw new Error(`Selector not found: ${selector}`);
  await new Promise((resolve) => setTimeout(resolve, 800));
  scrollResult = await send('Runtime.evaluate', {
    expression: `(() => { const target = document.querySelector(${JSON.stringify(selector)}); if (!target) return false; target.scrollIntoView({ block: 'start' }); return true; })()`,
    returnByValue: true,
  });
  if (!scrollResult.result.value) throw new Error(`Selector not found after layout settled: ${selector}`);
  await new Promise((resolve) => setTimeout(resolve, 250));

  const metricsResult = await send('Runtime.evaluate', {
    expression: `JSON.stringify({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth, scrollY: window.scrollY, targetTop: Math.round(document.querySelector(${JSON.stringify(selector)})?.getBoundingClientRect().top ?? -1), heading: document.querySelector(${JSON.stringify(selector)})?.querySelector('h1,h2,h3')?.textContent?.trim() ?? '' })`,
    returnByValue: true,
  });
  const capture = await send('Page.captureScreenshot', {
    format: 'png',
    fromSurface: true,
    captureBeyondViewport: false,
  });
  await writeFile(output, Buffer.from(capture.data, 'base64'));
  process.stdout.write(`${metricsResult.result.value}\n${output}\n`);
} finally {
  socket.close();
  chrome.kill();
}
