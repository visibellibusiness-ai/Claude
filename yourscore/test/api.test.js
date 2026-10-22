'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');

process.env.YS_DATA_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'ys-'));
process.env.YS_RETRY_DELAYS = '50,50';
const { start, createPlatform } = require('../src/server');
const { validateScore } = require('../src/rules');

// PNG valido di 1x1 pixel, al posto di una firma vera.
const PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';

let server, base, key, hookSecret;
const received = [];
let hookServer;

async function call(method, p, body, token = key) {
  const r = await fetch(base + p, { method, headers: { authorization: 'Bearer ' + token, 'content-type': 'application/json' }, body: body && JSON.stringify(body) });
  return { status: r.status, body: await r.json() };
}

test.before(async () => {
  server = await start(0);
  base = `http://localhost:${server.address().port}`;
  key = createPlatform('Piattaforma di prova').api_key;
  hookServer = http.createServer((req, res) => {
    let b = ''; req.on('data', c => b += c); req.on('end', () => { received.push({ headers: req.headers, body: b }); res.end('ok'); });
  });
  await new Promise(r => hookServer.listen(0, r));
});
test.after(() => { server.close(); hookServer.close(); });

test('regole di punteggio', () => {
  assert.ok(validateScore('pickleball_11', [[11, 7]]).ok);
  assert.ok(validateScore('pickleball_11', [[13, 11]]).ok);
  assert.ok(!validateScore('pickleball_11', [[11, 10]]).ok);
  assert.ok(!validateScore('pickleball_11', [[14, 11]]).ok);
  assert.deepStrictEqual(validateScore('padel_bo3', [[6, 4], [3, 6], [7, 6]]).winner, 0);
  assert.ok(!validateScore('padel_bo3', [[6, 5]]).ok);
  assert.ok(validateScore('padel_bo3_super', [[6, 4], [4, 6], [10, 8]]).ok);
  assert.ok(!validateScore('padel_bo3', [[6, 4], [6, 4], [6, 4]]).ok, 'set in più dopo la fine');
  assert.ok(!validateScore('tennis_bo3', [[6, 4]]).ok, 'partita non finita');
  assert.ok(validateScore('badminton_bo3', [[30, 29], [21, 15]]).ok);
  assert.ok(validateScore('table_tennis_bo5', [[11, 9], [9, 11], [11, 5], [12, 10]]).ok);
});

test('flusso completo: piattaforma → tablet → referto certificato → webhook', async () => {
  let r = await call('POST', '/v1/webhooks', { url: `http://localhost:${hookServer.address().port}/hook`, events: ['*'] });
  assert.strictEqual(r.status, 200);
  hookSecret = r.body.secret;

  r = await call('PUT', '/v1/events/T-2026-ROMA', { name: 'Open di Roma', format: 'pickleball_11' });
  assert.strictEqual(r.status, 200);

  r = await call('POST', '/v1/events/T-2026-ROMA/matches/batch', { matches: [
    { external_id: 'M1', court: '1', round: 'Girone A', teams: [
      { players: [{ external_id: 'p1', name: 'Mario Rossi' }, { external_id: 'p2', name: 'Luca Bianchi' }] },
      { players: [{ external_id: 'p3', name: 'Anna Verdi' }, { external_id: 'p4', name: 'Sara Neri' }] }] },
    { external_id: 'M2', court: '2', teams: [{ players: [{ external_id: 'p5', name: 'A' }] }, { players: [{ external_id: 'p6', name: 'B' }] }] },
    { external_id: 'BAD', teams: [{ players: [] }] },
  ] });
  assert.deepStrictEqual(r.body.results.map(x => x.ok), [true, true, false]);

  r = await call('POST', '/v1/events/T-2026-ROMA/devices', { court: '1' });
  const device = r.body.token;
  assert.match(r.body.tablet_url, /\/court\/#token=dt_/);

  r = await call('GET', '/v1/device/matches', null, device);
  assert.strictEqual(r.body.matches.length, 1, 'il tablet del campo 1 vede solo le partite del campo 1');
  const matchId = r.body.matches[0].id;

  // Punteggio impossibile
  r = await call('POST', `/v1/device/matches/${matchId}/scoresheet`, { score: [[11, 10]], signatures: [] }, device);
  assert.strictEqual(r.status, 422);
  // Manca una firma
  const sigs = ['p1', 'p2', 'p3'].map(p => ({ player_external_id: p, image_png_base64: PNG }));
  r = await call('POST', `/v1/device/matches/${matchId}/scoresheet`, { score: [[11, 7]], signatures: sigs }, device);
  assert.strictEqual(r.body.error.code, 'missing_signatures');
  assert.deepStrictEqual(r.body.error.details.missing, ['p4']);
  // Tutto in regola
  sigs.push({ player_external_id: 'p4', image_png_base64: 'data:image/png;base64,' + PNG });
  r = await call('POST', `/v1/device/matches/${matchId}/scoresheet`, { client_id: 'c-1', score: [[11, 7]], signatures: sigs }, device);
  assert.strictEqual(r.status, 200);
  const sheet = r.body;
  assert.strictEqual(sheet.status, 'certified');
  assert.deepStrictEqual(sheet.winner_player_external_ids, ['p1', 'p2']);
  assert.ok(!('image_png_base64' in sheet.signatures[0]), 'le immagini delle firme non escono nei webhook');

  // Invio ripetuto dopo una caduta di rete: stesso referto, nessun doppione
  r = await call('POST', `/v1/device/matches/${matchId}/scoresheet`, { client_id: 'c-1', score: [[11, 7]], signatures: sigs }, device);
  assert.strictEqual(r.body.id, sheet.id);

  // Verifica pubblica
  r = await call('GET', `/v1/verify/${sheet.id}`);
  assert.strictEqual(r.body.valid, true);

  // Webhook firmato con HMAC
  await new Promise(res => setTimeout(res, 200));
  const hook = received.find(h => JSON.parse(h.body).type === 'scoresheet.certified');
  assert.ok(hook, 'webhook ricevuto');
  const [t, v1] = hook.headers['yourscore-signature'].split(',').map(x => x.split('=')[1]);
  assert.strictEqual(crypto.createHmac('sha256', hookSecret).update(`${t}.${hook.body}`).digest('hex'), v1);
  assert.strictEqual(JSON.parse(hook.body).data.scoresheet.match.external_id, 'M1');

  // La piattaforma vede il referto anche via polling, con le proprie chiavi
  r = await call('GET', '/v1/scoresheets?event=T-2026-ROMA');
  assert.strictEqual(r.body[0].match.external_id, 'M1');
});

test('manomissione del referto rilevata', async () => {
  const db = path.join(process.env.YS_DATA_DIR, 'db.json');
  const data = JSON.parse(fs.readFileSync(db, 'utf8'));
  const id = Object.keys(data.scoresheets)[0];
  // Si simula qualcuno che modifica il punteggio nel server dopo la certificazione.
  const { start: start2 } = require('../src/server');
  server.close();
  data.scoresheets[id].score = [[7, 11]];
  fs.writeFileSync(db, JSON.stringify(data));
  server = await start2(0);
  base = `http://localhost:${server.address().port}`;
  const r = await call('GET', `/v1/verify/${id}`);
  assert.strictEqual(r.body.valid, false);
  assert.match(r.body.reason, /alterato/);
});

test('contestazione e annullamento', async () => {
  let r = await call('POST', '/v1/events/T-2026-ROMA/devices', {});
  const device = r.body.token;
  r = await call('GET', '/v1/device/matches', null, device);
  const m2 = r.body.matches.find(m => m.external_id === 'M2');
  r = await call('POST', `/v1/device/matches/${m2.id}/scoresheet`, { score: [[11, 4]], signatures: [{ player_external_id: 'p5', image_png_base64: PNG }], dispute: { player_external_id: 'p6', note: 'era 4-11' } }, device);
  assert.strictEqual(r.body.status, 'disputed');
  assert.strictEqual(r.body.certificate, undefined);

  r = await call('POST', `/v1/device/matches/${m2.id}/scoresheet`, { score: [[4, 11]], signatures: ['p5', 'p6'].map(p => ({ player_external_id: p, image_png_base64: PNG })) }, device);
  assert.strictEqual(r.body.status, 'certified');
  const id = r.body.id;

  r = await call('POST', `/v1/scoresheets/${id}/void`, { reason: 'errore di trascrizione' });
  assert.strictEqual(r.body.status, 'voided');
  r = await call('GET', '/v1/events/T-2026-ROMA/matches');
  assert.strictEqual(r.body.find(m => m.external_id === 'M2').status, 'open');
});

test('sicurezza: chiavi e tablet', async () => {
  let r = await call('GET', '/v1/events', null, 'ys_live_sbagliata');
  assert.strictEqual(r.status, 401);
  r = await call('GET', '/v1/device/matches', null, key);
  assert.strictEqual(r.status, 401, 'la API key della piattaforma non vale come tablet');
  const other = createPlatform('Altra piattaforma').api_key;
  r = await call('GET', '/v1/events/T-2026-ROMA/matches', null, other);
  assert.strictEqual(r.status, 404, 'una piattaforma non vede gli eventi di un\'altra');
});
