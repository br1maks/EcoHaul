import assert from 'node:assert/strict';
import { test } from 'node:test';
import { loadTypeScript } from './load-typescript.mjs';

function setup(post) {
  let reject;
  let access = 'access-old', refresh = 'refresh-old';
  let saves = 0, clears = 0, requests = 0;
  const client = async (request) => ({ request });
  client.interceptors = {
    request: { use() {} },
    response: { use(ok, failed) { reject = failed; } },
  };
  const axios = {
    create: () => client,
    isAxiosError: (error) => Boolean(error?.isAxiosError),
    post: (...args) => { requests++; return post(...args); },
  };
  loadTypeScript('src/lib/api/client.ts', {
    axios: { default: axios }, '@/config/env': { config: { apiUrl: 'http://localhost' } },
    './tokens': {
      getAccessToken: () => access, getRefreshToken: () => refresh,
      setTokens: (a, r) => { access = a; refresh = r; saves++; },
      clearTokens: () => { access = refresh = null; clears++; },
    },
  });
  return {
    fail: (authorization = 'Bearer access-old') => reject({ isAxiosError: true, response: { status: 401 },
      config: { url: '/users/me', headers: { Authorization: authorization } } }),
    change: (a, r) => { access = a; refresh = r; },
    state: () => ({ access, refresh, saves, clears, requests }),
  };
}

test('simultaneous unauthorized responses share one refresh rotation', async () => {
  let finish;
  const api = setup(() => new Promise((resolve) => { finish = resolve; }));
  const first = api.fail(), second = api.fail();
  finish({ data: { access_token: 'access-new', refresh_token: 'refresh-new' } });
  const results = await Promise.all([first, second]);
  assert.equal(api.state().requests, 1);
  assert.equal(api.state().saves, 1);
  assert.ok(results.every((item) => item.request.headers.Authorization === 'Bearer access-new'));
});

test('late unauthorized response reuses the newer access token without rotating again', async () => {
  const api = setup(() => assert.fail('unexpected refresh'));
  api.change('access-new', 'refresh-new');
  const result = await api.fail();
  assert.equal(result.request.headers.Authorization, 'Bearer access-new');
  assert.equal(api.state().requests, 0);
});

test('an in-flight refresh cannot restore credentials after logout', async () => {
  let finish;
  const api = setup(() => new Promise((resolve) => { finish = resolve; }));
  const request = api.fail();
  api.change(null, null);
  finish({ data: { access_token: 'access-new', refresh_token: 'refresh-new' } });
  await assert.rejects(request, /Сессия изменилась/);
  assert.equal(api.state().access, null);
  assert.equal(api.state().saves, 0);
});

test('temporary refresh outage preserves credentials while explicit rejection clears them', async () => {
  let api = setup(async () => { throw { isAxiosError: true, response: { status: 503 } }; });
  await assert.rejects(api.fail());
  assert.equal(api.state().refresh, 'refresh-old');
  assert.equal(api.state().clears, 0);
  api = setup(async () => { throw { isAxiosError: true, response: { status: 401 } }; });
  await assert.rejects(api.fail());
  assert.equal(api.state().refresh, null);
  assert.equal(api.state().clears, 1);
});
