import assert from 'node:assert/strict';
import { test } from 'node:test';
import { loadTypeScript } from './load-typescript.mjs';

class Socket {
  static OPEN = 1;
  static CONNECTING = 0;
  static instances = [];
  readyState = Socket.OPEN;
  constructor(url) { this.url = url; Socket.instances.push(this); }
  close() { this.readyState = 3; this.onclose?.(); }
  receive(message) { this.onmessage?.({ data: JSON.stringify(message) }); }
}

test('a publication retried after a lost acknowledgement is handled once across reconnects', async (context) => {
  const original = globalThis.WebSocket;
  globalThis.WebSocket = Socket;
  context.after(() => { globalThis.WebSocket = original; });
  const { wsManager } = loadTypeScript('src/lib/api/websocket.ts', {
    '@/config/env': { config: { wsUrl: 'ws://localhost/test' } },
    './tokens': { getAccessToken: () => 'local-test-token' },
    './client': { apiClient: { post: async () => ({ data: { ticket: 'one-use-ticket-with-32-bytes' } }) } },
  });
  const events = [];
  wsManager.on('ORDER_STATUS_CHANGED', (message) => events.push(message));
  const message = { event_id: 'same-durable-event', type: 'ORDER_STATUS_CHANGED', data: { new_status: 'ARRIVED' } };
  await wsManager.connect('local-test-token');
  const staleSocket = Socket.instances.at(-1);
  assert.ok(!staleSocket.url.includes('local-test-token'));
  assert.ok(staleSocket.url.includes('ticket='));
  Socket.instances.at(-1).receive(message);
  Socket.instances.at(-1).receive(message);
  wsManager.disconnect();
  await wsManager.connect('local-test-token');
  staleSocket.receive({ ...message, event_id: 'stale-socket-event' });
  Socket.instances.at(-1).receive(message);
  Socket.instances.at(-1).receive({ ...message, event_id: 'next-durable-event' });
  assert.equal(events.length, 2);
  wsManager.disconnect();
});

test('inbox snapshots merge with in-flight realtime entries without double counting', () => {
  const { useNotificationsStore: store } = loadTypeScript('src/store/notifications.store.ts');
  const notification = (id, is_read = false) => ({ id, is_read, title: id, created_at: '2026-01-01T00:00:00Z' });
  store.getState().addNotification(notification('live'));
  store.getState().addNotification(notification('live'));
  assert.equal(store.getState().unreadCount, 1);
  store.getState().markAsRead('missing');
  assert.equal(store.getState().unreadCount, 1);
  store.getState().mergeNotifications([notification('history'), notification('live', true)]);
  assert.equal(store.getState().notifications.length, 2);
  assert.equal(store.getState().unreadCount, 1);
  assert.equal(store.getState().notifications.find((item) => item.id === 'live').is_read, true);
  store.getState().markAllAsRead();
  store.getState().markAsRead('history');
  assert.equal(store.getState().unreadCount, 0);
});

test('a ticket response arriving after disconnect cannot open a socket', async (context) => {
  const original = globalThis.WebSocket;
  globalThis.WebSocket = Socket;
  context.after(() => { globalThis.WebSocket = original; });
  let finish;
  const { wsManager } = loadTypeScript('src/lib/api/websocket.ts', {
    '@/config/env': { config: { wsUrl: 'ws://localhost/test' } },
    './tokens': { getAccessToken: () => 'local-test-token' },
    './client': { apiClient: { post: () => new Promise((resolve) => { finish = resolve; }) } },
  });
  const before = Socket.instances.length;
  const opening = wsManager.connect('local-test-token');
  wsManager.disconnect();
  finish({ data: { ticket: 'unused-ticket' } });
  await opening;
  assert.equal(Socket.instances.length, before);
});

test('a fresh inbox snapshot removes deleted rows and preserves newly arriving events', () => {
  const { useNotificationsStore: store } = loadTypeScript('src/store/notifications.store.ts');
  const notification = (id, is_read = false) => ({ id, is_read, title: id, created_at: '2026-01-01T00:00:00Z' });
  store.getState().setNotifications([notification('deleted-on-server'), notification('read')]);
  const snapshot = store.getState().notifications;
  store.getState().markAllAsRead();
  store.getState().addNotification(notification('arrived-during-fetch'));
  store.getState().mergeNotifications([notification('read')], snapshot);
  assert.deepEqual(new Set(store.getState().notifications.map((item) => item.id)),
    new Set(['read', 'arrived-during-fetch']));
  assert.equal(store.getState().notifications.find((item) => item.id === 'read').is_read, true);
  assert.equal(store.getState().unreadCount, 1);
  const generation = store.getState().generation;
  store.getState().clearNotifications();
  assert.ok(store.getState().generation > generation);
});
