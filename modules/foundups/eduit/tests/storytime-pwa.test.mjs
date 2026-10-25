import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';

const source = fs.readFileSync(new URL('../../../../public/eduit/storytime/pwa.js', import.meta.url), 'utf8')
  .replace('__STORYTIME_PWA_ORIGINS__', 'https://storytime.eduit.org');
function surface(origin = 'https://storytime.eduit.org') {
  const element = () => ({hidden: true, disabled: false, textContent: '', handlers: {},
    addEventListener(name, handler) {this.handlers[name] = handler;}});
  const nodes = Object.fromEntries(['install-app', 'update-app', 'pwa-status'].map(id => [id, element()]));
  const video = {...element(), pause() {}, querySelector() {return element();}};
  const window = {...element(), isSecureContext: true};
  const waiting = {...element(), state: 'installed', messages: [], postMessage(message) {this.messages.push(message);}};
  const registration = {...element(), waiting};
  const serviceWorker = {...element(), controller: {}, registrations: [], register(...args) {
    this.registrations.push(args); return Promise.resolve(registration);
  }};
  let reloads = 0;
  const context = {window, document: {getElementById: id => nodes[id], querySelector: () => video},
    navigator: {onLine: true, serviceWorker}, location: {origin, reload: () => {reloads++;}}};
  vm.runInNewContext(source, context);
  return {nodes, window, waiting, serviceWorker, get reloads() {return reloads;}};
}

test('registration occurs only on the exact allowed standalone origin', async () => {
  const standalone = surface();
  await Promise.resolve();
  assert.equal(standalone.serviceWorker.registrations.length, 1);
  assert.equal(standalone.serviceWorker.registrations[0][0], '/storytime-sw.js');
  assert.equal(standalone.serviceWorker.registrations[0][1].scope, '/');
  for (const host of ['https://foundups.com', 'https://another.web.app', 'https://storytime.eduit.org.attacker.example']) {
    assert.equal(surface(host).serviceWorker.registrations.length, 0);
  }
});

test('waiting revisions do not activate or reload until the explicit update action', async () => {
  const page = surface();
  await Promise.resolve();
  assert.equal(page.nodes['update-app'].hidden, false);
  assert.equal(page.waiting.messages.length, 0);
  assert.equal(page.reloads, 0);
  page.nodes['update-app'].handlers.click();
  assert.equal(page.waiting.messages.length, 1);
  assert.equal(page.waiting.messages[0].type, 'STORYTIME_ACTIVATE');
  assert.equal(page.reloads, 0);
  page.waiting.state = 'activated';
  page.waiting.handlers.statechange();
  page.serviceWorker.handlers.controllerchange();
  assert.equal(page.reloads, 1);
});

test('install button appears only when a browser supplies its install prompt', async () => {
  const page = surface();
  await Promise.resolve();
  assert.equal(page.nodes['install-app'].hidden, true);
  let prompted = false;
  page.window.handlers.beforeinstallprompt({preventDefault() {}, prompt: async () => {prompted = true;},
    userChoice: Promise.resolve({outcome: 'accepted'})});
  assert.equal(page.nodes['install-app'].hidden, false);
  await page.nodes['install-app'].handlers.click();
  assert.equal(prompted, true);
  assert.match(page.nodes['pwa-status'].textContent, /installation requested/);
  page.window.handlers.appinstalled();
  assert.equal(page.nodes['pwa-status'].textContent, 'Story Time is installed.');
});
