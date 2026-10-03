/** Execute the exact documented TypeScript examples against fault-injecting clients.
 * No credentials, dependencies, network, or live provider sessions are used.
 * Run with Node >=24: node --test scripts/migration-tests/test-examples.mjs
 */
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { after, test } from 'node:test';

const doc = new URL('../../plugins/notte-migrate/skills/migrate-to-notte/references/notte-sessions.md', import.meta.url);
const source = await readFile(doc, 'utf8');
const examples = [...source.matchAll(/```typescript\n([\s\S]*?)```/g)].map(m => m[1]);
assert.equal(examples.length, 2, 'Expected Playwright and Puppeteer examples');
const temp = await mkdtemp(path.join(os.tmpdir(), 'notte-migration-examples-'));
after(() => rm(temp, { recursive: true, force: true }));
for (const [name, content] of Object.entries({
  'notte-sdk': 'export class NotteClient { Session(options) { globalThis.fixture.options = options; return globalThis.fixture.session; } }',
  'playwright-core': 'export const chromium = { connectOverCDP: (...args) => globalThis.fixture.connect(...args) };',
  'puppeteer-core': 'export default { connect: (...args) => globalThis.fixture.connect(...args) };',
})) {
  const dir = path.join(temp, 'node_modules', name);
  await mkdir(dir, { recursive: true });
  await writeFile(path.join(dir, 'package.json'), JSON.stringify({ name, type: 'module', exports: './index.js' }));
  await writeFile(path.join(dir, 'index.js'), content);
}
const modules = [];
for (let i = 0; i < examples.length; i++) {
  const file = path.join(temp, `example-${i}.mts`);
  await writeFile(file, examples[i]);
  modules.push(await import(pathToFileURL(file)));
}

function fixture(failures, { emptyPage = false, missingContext = false } = {}) {
  const calls = [];
  const errors = Object.fromEntries(failures.map(stage => [stage, new Error(`${stage} failed`)]));
  const hit = stage => { calls.push(stage); if (errors[stage]) throw errors[stage]; };
  const page = { goto: async () => hit('goto'), title: async () => { hit('title'); return 'Expected application title'; } };
  const context = { pages: () => emptyPage ? [] : [page], newPage: async () => { hit('newPage'); return page; } };
  const browser = {
    contexts: () => missingContext ? [] : [context],
    defaultBrowserContext: () => missingContext ? undefined : context,
    close: async () => hit('clientCleanup'),
    disconnect: async () => hit('clientCleanup'),
  };
  const session = {
    start: async () => hit('start'),
    cdpUrl: async () => { hit('cdp'); return 'wss://fixture.invalid/browser'; },
    stop: async () => hit('stop'),
    // This double follows the SDK's documented callback/stop error precedence.
    async use(callback) {
      await this.start();
      let failed = false;
      try { return await callback(this); }
      catch (e) { failed = true; console.warn(`Session exiting because of exception: ${String(e)}`); throw e; }
      finally { try { await this.stop(); } catch (e) { if (!failed) throw e; } }
    },
  };
  return { calls, errors, session, connect: async () => { hit('connect'); return browser; } };
}

for (const [i, driver] of ['Playwright', 'Puppeteer'].entries()) {
  for (const failures of [[], ['start'], ['cdp'], ['connect'], ['goto'], ['title'], ['clientCleanup'], ['stop'], ['goto', 'clientCleanup'], ['goto', 'stop'], ['goto', 'clientCleanup', 'stop'], ['connect', 'stop']]) {
    test(`${driver}: ${failures.join(' + ') || 'success'}`, async () => {
      const f = fixture(failures);
      globalThis.fixture = f;
      if (failures.length) {
        await assert.rejects(modules[i].readTitle('https://fixture.invalid'), error => error === f.errors[failures[0]], 'Preserve the original failure');
      } else {
        assert.equal(await modules[i].readTitle('https://fixture.invalid'), 'Expected application title');
      }
      assert.equal(f.calls.filter(c => c === 'stop').length, failures.includes('start') ? 0 : 1, 'Stop every successfully started session');
      const connected = !failures.some(c => ['start', 'cdp', 'connect'].includes(c));
      assert.equal(f.calls.filter(c => c === 'clientCleanup').length, connected ? 1 : 0);
      assert.equal(f.options.max_duration_minutes, 5);
      assert.equal(f.options.idle_timeout_minutes, 2);
    });
  }
  test(`${driver}: reuse default context when initial page is absent`, async () => {
    const f = fixture([], { emptyPage: true }); globalThis.fixture = f;
    assert.equal(await modules[i].readTitle('https://fixture.invalid'), 'Expected application title');
    assert.equal(f.calls.filter(c => c === 'newPage').length, 1);
    assert.equal(f.calls.filter(c => c === 'stop').length, 1);
  });
  test(`${driver}: missing context still cleans up`, async () => {
    const f = fixture([], { missingContext: true }); globalThis.fixture = f;
    await assert.rejects(modules[i].readTitle('https://fixture.invalid'));
    assert.ok(f.calls.includes('clientCleanup'));
    assert.ok(f.calls.includes('stop'));
  });
}

for (const [i, driver] of ['Playwright', 'Puppeteer'].entries()) {
  test(`${driver}: transport errors are not logged by the example`, async () => {
    const f = fixture(['connect']);
    f.errors.connect.message = 'connect failed: wss://fixture.invalid?apiKey=synthetic-secret';
    globalThis.fixture = f;
    const original = { warn: console.warn, error: console.error, log: console.log };
    const output = [];
    for (const key of Object.keys(original)) console[key] = (...args) => output.push(args.join(' '));
    try {
      await assert.rejects(modules[i].readTitle('https://fixture.invalid'), error => error === f.errors.connect);
      assert.equal(output.length, 0, 'Caller owns sanitized error reporting');
    } finally {
      Object.assign(console, original);
    }
  });
}
