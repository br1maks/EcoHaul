import assert from 'node:assert/strict';
import { test } from 'node:test';
import { loadTypeScript } from './load-typescript.mjs';

function setup(context, post) {
  const original = globalThis.sessionStorage;
  const memory = new Map();
  globalThis.sessionStorage = {
    getItem: (key) => memory.get(key) ?? null,
    setItem: (key, value) => memory.set(key, value),
  };
  context.after(() => { globalThis.sessionStorage = original; });
  return () => loadTypeScript('src/lib/api/checkout.ts', {
    './client': { apiClient: { post } },
    './tokens': { getAccessToken: () => `test.${btoa(JSON.stringify({ sub: 'test-user' }))}.test` },
  });
}

const result = { payment_id: 'test-payment', payment_url: 'https://example.test/pay',
  status: 'PENDING', creation_state: 'READY', amount: 5 };

test('checkout retry identity survives a lost response and module reload', async (context) => {
  const keys = [];
  const reload = setup(context, async (path, data, config) => {
    keys.push(config.headers['Idempotency-Key']);
    if (keys.length === 1) throw new Error('lost network response');
    return { data: result };
  });
  await assert.rejects(reload().performCheckout('/payments', { amount: 5 }), /lost network response/);
  assert.equal((await reload().performCheckout('/payments', { amount: 5 })).payment_id, 'test-payment');
  assert.equal(keys.length, 2);
  assert.equal(keys[0], keys[1]);
});

test('parallel browser calls share one operation', async (context) => {
  let calls = 0;
  const reload = setup(context, async () => { calls++; return { data: result }; });
  const { performCheckout } = reload();
  const first = performCheckout('/payments', { amount: 5 });
  const second = performCheckout('/payments', { amount: 5 });
  assert.equal(first, second);
  await first;
  assert.equal(calls, 1);
});

test('only a confirmed terminal response releases the saved retry identity', async (context) => {
  const keys = [];
  const reload = setup(context, async (path, data, config) => {
    keys.push(config.headers['Idempotency-Key']);
    return { data: { ...result, status: 'COMPLETED', payment_url: null } };
  });
  const { performCheckout } = reload();
  assert.match((await performCheckout('/payments', { amount: 5 })).payment_url, /^\/payment\/success/);
  await performCheckout('/payments', { amount: 5 });
  assert.notEqual(keys[0], keys[1]);
});
