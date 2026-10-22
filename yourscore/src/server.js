'use strict';
// Your Score: referti di partita firmati dai giocatori e certificati, collegabili a qualsiasi
// piattaforma di tornei tramite API REST + webhook. Nessuna dipendenza esterna.
const http = require('node:http');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { FORMATS, validateScore } = require('./rules');

const DATA_DIR = process.env.YS_DATA_DIR || path.join(__dirname, '..', 'data');
const PUBLIC_DIR = path.join(__dirname, '..', 'public');
const BASE_URL = (process.env.YS_BASE_URL || '').replace(/\/$/, '');
const MAX_BODY = 3 * 1024 * 1024;
const RETRY_DELAYS = (process.env.YS_RETRY_DELAYS || '2000,15000,60000').split(',').map(Number);

// ---------- Archivio (file JSON, scrittura atomica) ----------
const DB_FILE = path.join(DATA_DIR, 'db.json');
let db;
function loadDb() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  db = fs.existsSync(DB_FILE) ? JSON.parse(fs.readFileSync(DB_FILE, 'utf8')) : {};
  for (const k of ['platforms', 'events', 'matches', 'devices', 'scoresheets', 'webhooks', 'deliveries']) db[k] ||= {};
  db.chain ||= {};
}
function saveDb() {
  const tmp = DB_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(db));
  fs.renameSync(tmp, DB_FILE);
}

// ---------- Chiavi di certificazione ----------
let signKey, publicKeyPem, keyId;
function loadKeys() {
  const file = path.join(DATA_DIR, 'signing-key.pem');
  if (!fs.existsSync(file)) {
    const { privateKey } = crypto.generateKeyPairSync('ed25519');
    fs.writeFileSync(file, privateKey.export({ type: 'pkcs8', format: 'pem' }), { mode: 0o600 });
  }
  signKey = crypto.createPrivateKey(fs.readFileSync(file));
  publicKeyPem = crypto.createPublicKey(signKey).export({ type: 'spki', format: 'pem' });
  keyId = 'ys-' + sha256(publicKeyPem).slice(0, 16);
}

// ---------- Utilità ----------
const sha256 = s => crypto.createHash('sha256').update(s).digest('hex');
const rid = (prefix, n = 12) => prefix + '_' + crypto.randomBytes(n).toString('base64url');
const now = () => new Date().toISOString();

// JSON con chiavi ordinate: lo stesso referto produce sempre la stessa impronta.
function canonical(v) {
  if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
  if (v && typeof v === 'object') return '{' + Object.keys(v).sort().filter(k => v[k] !== undefined).map(k => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
  return JSON.stringify(v);
}

class HttpError extends Error {
  constructor(status, code, message, details) { super(message); this.status = status; this.code = code; this.details = details; }
}
const bad = (msg, details) => new HttpError(400, 'invalid_request', msg, details);
const notFound = what => new HttpError(404, 'not_found', `${what} non trovato`);

function str(v, name, { required = true, max = 200 } = {}) {
  if (v == null || v === '') { if (required) throw bad(`campo obbligatorio: ${name}`); return undefined; }
  if (typeof v !== 'string' && typeof v !== 'number') throw bad(`${name} deve essere una stringa`);
  v = String(v).trim();
  if (v.length > max) throw bad(`${name} troppo lungo (max ${max})`);
  return v;
}

function baseUrl(req) {
  if (BASE_URL) return BASE_URL;
  const proto = req.headers['x-forwarded-proto'] || 'http';
  return `${proto}://${req.headers.host}`;
}

// ---------- Autenticazione ----------
function bearer(req) {
  const h = req.headers.authorization || '';
  return h.startsWith('Bearer ') ? h.slice(7).trim() : null;
}
function authPlatform(req) {
  const t = bearer(req);
  const p = t && Object.values(db.platforms).find(p => p.key_hash === sha256(t));
  if (!p) throw new HttpError(401, 'unauthorized', 'API key mancante o non valida');
  return p;
}
function authDevice(req) {
  const t = bearer(req);
  const d = t && Object.values(db.devices).find(d => d.token_hash === sha256(t) && !d.revoked);
  if (!d) throw new HttpError(401, 'unauthorized', 'tablet non autorizzato: chiedi un nuovo link all\'organizzatore');
  d.last_seen_at = now();
  return d;
}

function createPlatform(name) {
  const key = 'ys_live_' + crypto.randomBytes(24).toString('base64url');
  const p = { id: rid('pl'), name, key_hash: sha256(key), created_at: now() };
  db.platforms[p.id] = p;
  saveDb();
  return { platform: p, api_key: key };
}

// ---------- Modello ----------
function eventByExt(platform, ext) {
  const e = Object.values(db.events).find(e => e.platform_id === platform.id && e.external_id === ext);
  if (!e) throw notFound('evento');
  return e;
}
function matchByExt(event, ext) {
  return Object.values(db.matches).find(m => m.event_id === event.id && m.external_id === ext);
}
function currentSheet(match) {
  return match.scoresheet_id ? db.scoresheets[match.scoresheet_id] : null;
}

function parseTeams(teams) {
  if (!Array.isArray(teams) || teams.length !== 2) throw bad('teams deve contenere esattamente 2 squadre');
  const seen = new Set();
  return teams.map((t, i) => {
    if (!t || !Array.isArray(t.players) || !t.players.length || t.players.length > 4) throw bad(`teams[${i}].players: da 1 a 4 giocatori`);
    const players = t.players.map((p, j) => {
      const id = str(p && p.external_id, `teams[${i}].players[${j}].external_id`, { max: 100 });
      if (seen.has(id)) throw bad(`giocatore ripetuto: ${id}`);
      seen.add(id);
      return { external_id: id, name: str(p.name, `teams[${i}].players[${j}].name`, { max: 100 }) };
    });
    return { name: str(t.name, `teams[${i}].name`, { required: false, max: 100 }) || players.map(p => p.name).join(' / '), players };
  });
}

function upsertMatch(platform, event, ext, body) {
  ext = str(ext, 'external_id', { max: 100 });
  const format = body.format || event.format;
  if (!FORMATS[format]) throw bad(`format sconosciuto: ${format}`, { allowed: Object.keys(FORMATS) });
  const data = {
    court: str(body.court, 'court', { required: false, max: 40 }) || null,
    round: str(body.round, 'round', { required: false, max: 80 }) || null,
    scheduled_at: str(body.scheduled_at, 'scheduled_at', { required: false, max: 40 }) || null,
    format,
    teams: parseTeams(body.teams),
  };
  let m = matchByExt(event, ext);
  if (m) {
    const sheet = currentSheet(m);
    if (sheet && sheet.status === 'certified' && canonical(m.teams) !== canonical(data.teams)) {
      throw new HttpError(409, 'already_certified', 'il referto è già certificato: annullalo prima di cambiare le squadre');
    }
    Object.assign(m, data, { updated_at: now() });
    if (m.status === 'cancelled') m.status = sheet && sheet.status === 'certified' ? 'certified' : 'open';
  } else {
    m = { id: rid('m'), platform_id: platform.id, event_id: event.id, external_id: ext, ...data, status: 'open', scoresheet_id: null, created_at: now(), updated_at: now() };
    db.matches[m.id] = m;
  }
  return m;
}

function publicMatch(m) {
  const e = db.events[m.event_id];
  return {
    id: m.id, external_id: m.external_id, event: { id: e.id, external_id: e.external_id, name: e.name },
    court: m.court, round: m.round, scheduled_at: m.scheduled_at, format: m.format, format_label: FORMATS[m.format].label,
    teams: m.teams, status: m.status, scoresheet_id: m.scoresheet_id,
  };
}

// Ciò che le piattaforme ricevono: niente immagini delle firme, solo la loro impronta.
function publicSheet(s, req) {
  const out = { ...s };
  delete out.platform_id;
  out.signatures = s.signatures.map(({ image_sha256, player_external_id, signed_at }) => ({ player_external_id, image_sha256, signed_at }));
  if (out.certificate) out.certificate = { ...out.certificate, verify_url: `${baseUrl(req)}/verify/${s.id}` };
  return out;
}

// ---------- Certificazione ----------
// Il contenuto certificato: partita, punteggio, chi ha firmato (impronte delle firme), tablet e ora.
function sealContent(s) {
  return {
    scoresheet_id: s.id, platform_id: s.platform_id, event: s.event, match: s.match, format: s.format,
    teams: s.teams, score: s.score, winner_team: s.winner_team, signatures: s.signatures.map(x => ({ p: x.player_external_id, h: x.image_sha256, t: x.signed_at })),
    referee: s.referee, device_id: s.device_id, created_at: s.created_at, prev_hash: s.certificate.prev_hash,
  };
}
function certify(s) {
  const prev = db.chain[s.platform_id] || null;
  s.certificate = { algorithm: 'Ed25519', key_id: keyId, prev_hash: prev };
  const hash = sha256(canonical(sealContent(s)));
  s.certificate.hash = hash;
  s.certificate.signature = crypto.sign(null, Buffer.from(hash), signKey).toString('base64');
  s.certified_at = now();
  s.status = 'certified';
  db.chain[s.platform_id] = hash;
}
function verifySheet(s) {
  if (!s.certificate) return { valid: false, reason: 'referto non certificato' };
  const hash = sha256(canonical(sealContent(s)));
  if (hash !== s.certificate.hash) return { valid: false, reason: 'il contenuto non corrisponde all\'impronta: referto alterato' };
  const ok = crypto.verify(null, Buffer.from(hash), crypto.createPublicKey(publicKeyPem), Buffer.from(s.certificate.signature, 'base64'));
  return ok ? { valid: true } : { valid: false, reason: 'firma di certificazione non valida' };
}

// ---------- Webhook ----------
function emit(platformId, type, sheet, req) {
  const hooks = Object.values(db.webhooks).filter(w => w.platform_id === platformId && !w.disabled && (w.events.includes(type) || w.events.includes('*')));
  const event = { id: rid('evt'), type, created_at: now(), data: { scoresheet: publicSheet(sheet, req) } };
  for (const w of hooks) {
    const d = { id: rid('dl'), webhook_id: w.id, event_id: event.id, type, attempts: 0, status: 'pending', created_at: now() };
    db.deliveries[d.id] = d;
    deliver(w, d, JSON.stringify(event));
  }
}
async function deliver(w, d, body) {
  d.attempts++;
  const ts = Math.floor(Date.now() / 1000);
  const sig = crypto.createHmac('sha256', w.secret).update(`${ts}.${body}`).digest('hex');
  try {
    const r = await fetch(w.url, {
      method: 'POST', body, signal: AbortSignal.timeout(10000),
      headers: { 'content-type': 'application/json', 'yourscore-signature': `t=${ts},v1=${sig}`, 'yourscore-event-id': d.event_id, 'user-agent': 'YourScore-Webhooks/1' },
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    d.status = 'delivered'; d.delivered_at = now();
  } catch (e) {
    d.last_error = String(e.message || e);
    if (d.attempts <= RETRY_DELAYS.length) {
      d.status = 'retrying';
      setTimeout(() => deliver(w, d, body), RETRY_DELAYS[d.attempts - 1]).unref();
    } else d.status = 'failed';
  }
  saveDb();
}

// ---------- Rotte ----------
const routes = [];
const route = (method, pattern, handler) => routes.push({ method, re: new RegExp('^' + pattern.replace(/:(\w+)/g, '(?<$1>[^/]+)') + '$'), handler });

route('GET', '/v1/formats', () => Object.entries(FORMATS).map(([id, f]) => ({ id, ...f })));
route('GET', '/v1/public-key', () => ({ key_id: keyId, algorithm: 'Ed25519', public_key_pem: publicKeyPem }));
route('GET', '/v1/me', req => { const p = authPlatform(req); return { id: p.id, name: p.name }; });

// Eventi (tornei): la piattaforma usa i propri ID, Your Score fa "upsert".
route('PUT', '/v1/events/:ext', (req, { ext }, body) => {
  const p = authPlatform(req);
  ext = str(ext, 'external_id', { max: 100 });
  const format = body.format || 'pickleball_11';
  if (!FORMATS[format]) throw bad(`format sconosciuto: ${format}`, { allowed: Object.keys(FORMATS) });
  let e = Object.values(db.events).find(e => e.platform_id === p.id && e.external_id === ext);
  const data = { name: str(body.name, 'name'), format, starts_at: str(body.starts_at, 'starts_at', { required: false, max: 40 }) || null, updated_at: now() };
  if (e) Object.assign(e, data);
  else { e = { id: rid('ev'), platform_id: p.id, external_id: ext, created_at: now(), ...data }; db.events[e.id] = e; }
  saveDb();
  return e;
});
route('GET', '/v1/events', req => { const p = authPlatform(req); return Object.values(db.events).filter(e => e.platform_id === p.id); });

route('PUT', '/v1/events/:ev/matches/:ext', (req, { ev, ext }, body) => {
  const p = authPlatform(req);
  const m = upsertMatch(p, eventByExt(p, ev), ext, body);
  saveDb();
  return publicMatch(m);
});
// Carico di un intero tabellone in una sola chiamata: ogni partita va o fallisce da sola.
route('POST', '/v1/events/:ev/matches/batch', (req, { ev }, body) => {
  const p = authPlatform(req);
  const e = eventByExt(p, ev);
  if (!Array.isArray(body.matches) || body.matches.length > 500) throw bad('matches: da 1 a 500 partite');
  const results = body.matches.map(mb => {
    try { return { external_id: mb.external_id, ok: true, match: publicMatch(upsertMatch(p, e, mb.external_id, mb)) }; }
    catch (err) { if (!(err instanceof HttpError)) throw err; return { external_id: mb && mb.external_id, ok: false, error: { code: err.code, message: err.message } }; }
  });
  saveDb();
  return { results };
});
route('GET', '/v1/events/:ev/matches', (req, { ev }, _b, q) => {
  const p = authPlatform(req);
  const e = eventByExt(p, ev);
  return Object.values(db.matches).filter(m => m.event_id === e.id && (!q.get('status') || m.status === q.get('status'))).map(publicMatch);
});
route('DELETE', '/v1/events/:ev/matches/:ext', (req, { ev, ext }) => {
  const p = authPlatform(req);
  const m = matchByExt(eventByExt(p, ev), ext);
  if (!m) throw notFound('partita');
  if (m.status === 'certified') throw new HttpError(409, 'already_certified', 'partita già certificata: annulla prima il referto');
  m.status = 'cancelled'; m.updated_at = now();
  saveDb();
  return publicMatch(m);
});

// Tablet: l'organizzatore crea un link per campo (o per tutto l'evento, se l'arbitro sceglie la partita).
route('POST', '/v1/events/:ev/devices', (req, { ev }, body) => {
  const p = authPlatform(req);
  const e = eventByExt(p, ev);
  const token = 'dt_' + crypto.randomBytes(24).toString('base64url');
  const d = { id: rid('dv'), platform_id: p.id, event_id: e.id, court: str(body.court, 'court', { required: false, max: 40 }) || null, label: str(body.label, 'label', { required: false }) || null, token_hash: sha256(token), created_at: now() };
  db.devices[d.id] = d;
  saveDb();
  return { id: d.id, court: d.court, label: d.label, token, tablet_url: `${baseUrl(req)}/court/#token=${token}` };
});
route('DELETE', '/v1/devices/:id', (req, { id }) => {
  const p = authPlatform(req);
  const d = db.devices[id];
  if (!d || d.platform_id !== p.id) throw notFound('tablet');
  d.revoked = true; saveDb();
  return { id, revoked: true };
});

// Referti: alternativa ai webhook per chi preferisce interrogare (polling).
route('GET', '/v1/scoresheets', (req, _p, _b, q) => {
  const p = authPlatform(req);
  const since = q.get('since'), ev = q.get('event');
  const e = ev ? eventByExt(p, ev) : null;
  return Object.values(db.scoresheets)
    .filter(s => s.platform_id === p.id && (!e || s.event.id === e.id) && (!since || (s.updated_at || s.created_at) > since))
    .sort((a, b) => (a.updated_at || a.created_at).localeCompare(b.updated_at || b.created_at))
    .map(s => publicSheet(s, req));
});
route('GET', '/v1/scoresheets/:id', (req, { id }) => {
  const p = authPlatform(req);
  const s = db.scoresheets[id];
  if (!s || s.platform_id !== p.id) throw notFound('referto');
  return publicSheet(s, req);
});
// Le immagini delle firme solo alla piattaforma proprietaria (dati personali).
route('GET', '/v1/scoresheets/:id/signatures', (req, { id }) => {
  const p = authPlatform(req);
  const s = db.scoresheets[id];
  if (!s || s.platform_id !== p.id) throw notFound('referto');
  return s.signatures.map(x => ({ player_external_id: x.player_external_id, signed_at: x.signed_at, image_png_base64: x.image_png_base64 }));
});
// Correzione di un errore: il referto resta nello storico come annullato e la partita si riapre.
route('POST', '/v1/scoresheets/:id/void', (req, { id }, body) => {
  const p = authPlatform(req);
  const s = db.scoresheets[id];
  if (!s || s.platform_id !== p.id) throw notFound('referto');
  if (s.status === 'voided') throw new HttpError(409, 'already_voided', 'referto già annullato');
  s.status = 'voided'; s.void_reason = str(body.reason, 'reason', { max: 500 }); s.updated_at = now();
  const m = db.matches[s.match.id];
  if (m && m.scoresheet_id === s.id) { m.status = 'open'; m.updated_at = now(); }
  saveDb();
  emit(p.id, 'scoresheet.voided', s, req);
  return publicSheet(s, req);
});

route('POST', '/v1/webhooks', (req, _p, body) => {
  const p = authPlatform(req);
  const url = str(body.url, 'url', { max: 500 });
  if (!/^https?:\/\//.test(url)) throw bad('url deve iniziare con http:// o https://');
  const events = Array.isArray(body.events) && body.events.length ? body.events : ['*'];
  const allowed = ['*', 'scoresheet.certified', 'scoresheet.disputed', 'scoresheet.voided'];
  if (!events.every(e => allowed.includes(e))) throw bad('eventi ammessi: ' + allowed.join(', '));
  const w = { id: rid('wh'), platform_id: p.id, url, events, secret: 'whsec_' + crypto.randomBytes(24).toString('base64url'), created_at: now() };
  db.webhooks[w.id] = w; saveDb();
  return w;
});
route('GET', '/v1/webhooks', req => {
  const p = authPlatform(req);
  return Object.values(db.webhooks).filter(w => w.platform_id === p.id).map(({ secret, ...w }) => w);
});
route('DELETE', '/v1/webhooks/:id', (req, { id }) => {
  const p = authPlatform(req);
  const w = db.webhooks[id];
  if (!w || w.platform_id !== p.id) throw notFound('webhook');
  delete db.webhooks[id]; saveDb();
  return { id, deleted: true };
});

// ---------- API del tablet ----------
route('GET', '/v1/device/matches', req => {
  const d = authDevice(req);
  const e = db.events[d.event_id];
  const matches = Object.values(db.matches)
    .filter(m => m.event_id === d.event_id && m.status !== 'cancelled' && (!d.court || m.court === d.court))
    .sort((a, b) => (a.scheduled_at || '').localeCompare(b.scheduled_at || '') || a.created_at.localeCompare(b.created_at))
    .map(publicMatch);
  return { device: { id: d.id, court: d.court, label: d.label }, event: { name: e.name }, matches };
});

route('POST', '/v1/device/matches/:id/scoresheet', (req, { id }, body) => {
  const d = authDevice(req);
  const m = db.matches[id];
  if (!m || m.event_id !== d.event_id || (d.court && m.court !== d.court)) throw notFound('partita');
  if (m.status === 'cancelled') throw new HttpError(409, 'match_cancelled', 'partita annullata dall\'organizzatore');
  const prev = currentSheet(m);
  if (prev && prev.status === 'certified') {
    // Lo stesso invio ripetuto (es. rete caduta dopo il salvataggio) restituisce il referto già certificato.
    if (body.client_id && prev.client_id === body.client_id) return publicSheet(prev, req);
    throw new HttpError(409, 'already_certified', 'questa partita ha già un referto certificato');
  }
  const v = validateScore(m.format, body.score);
  if (!v.ok) throw new HttpError(422, 'invalid_score', v.error);

  const players = m.teams.flatMap(t => t.players.map(p => p.external_id));
  const sigs = Array.isArray(body.signatures) ? body.signatures : [];
  const signatures = [];
  for (const s of sigs) {
    if (!s || !players.includes(s.player_external_id)) throw bad('firma di un giocatore che non è in questa partita');
    if (signatures.some(x => x.player_external_id === s.player_external_id)) throw bad('firma ripetuta');
    const img = str(s.image_png_base64, 'image_png_base64', { max: 400000 }).replace(/^data:image\/png;base64,/, '');
    if (!/^[A-Za-z0-9+/=]+$/.test(img) || !Buffer.from(img, 'base64').subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) throw bad('la firma deve essere un\'immagine PNG');
    signatures.push({ player_external_id: s.player_external_id, image_png_base64: img, image_sha256: sha256(Buffer.from(img, 'base64')), signed_at: str(s.signed_at, 'signed_at', { required: false, max: 40 }) || now() });
  }
  const dispute = body.dispute ? { note: str(body.dispute.note, 'dispute.note', { required: false, max: 1000 }) || '', raised_by: str(body.dispute.player_external_id, 'dispute.player_external_id', { required: false, max: 100 }) || null } : null;
  if (!dispute) {
    const missing = players.filter(p => !signatures.some(s => s.player_external_id === p));
    if (missing.length) throw new HttpError(422, 'missing_signatures', 'mancano le firme di tutti i giocatori', { missing });
  }

  const e = db.events[m.event_id];
  const s = {
    id: rid('ss'), platform_id: m.platform_id, client_id: str(body.client_id, 'client_id', { required: false, max: 100 }) || null,
    status: dispute ? 'disputed' : 'signed',
    event: { id: e.id, external_id: e.external_id, name: e.name },
    match: { id: m.id, external_id: m.external_id, court: m.court, round: m.round },
    format: m.format, teams: m.teams, score: v.ok ? body.score : null, winner_team: v.winner, sets_won: v.sets_won,
    winner_player_external_ids: m.teams[v.winner].players.map(p => p.external_id),
    signatures, referee: body.referee ? { name: str(body.referee.name, 'referee.name', { max: 100 }) } : null,
    dispute, device_id: d.id, created_at: now(), updated_at: now(),
  };
  if (prev && prev.status !== 'voided') { prev.status = 'superseded'; prev.updated_at = now(); }
  if (!dispute) certify(s);
  db.scoresheets[s.id] = s;
  m.scoresheet_id = s.id; m.status = dispute ? 'disputed' : 'certified'; m.updated_at = now();
  saveDb();
  emit(m.platform_id, dispute ? 'scoresheet.disputed' : 'scoresheet.certified', s, req);
  return publicSheet(s, req);
});

// ---------- Verifica pubblica ----------
route('GET', '/v1/verify/:id', (req, { id }) => {
  const s = db.scoresheets[id];
  if (!s) throw notFound('referto');
  return { id: s.id, status: s.status, ...verifySheet(s), event: s.event.name, teams: s.teams.map(t => t.name), score: s.score, winner_team: s.winner_team, certified_at: s.certified_at, hash: s.certificate && s.certificate.hash, key_id: s.certificate && s.certificate.key_id };
});

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
function verifyPage(s) {
  const v = verifySheet(s);
  const statusText = { certified: 'Referto certificato', voided: 'Referto annullato', superseded: 'Referto sostituito da uno più recente', disputed: 'Risultato contestato', signed: 'Firmato' }[s.status] || s.status;
  const ok = v.valid && s.status === 'certified';
  return `<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Verifica referto</title><style>
:root{--bg:#f4f6f3;--card:#fff;--text:#17201a;--muted:#5d6b62;--ok:#15803d;--ko:#b91c1c;--line:#dfe5e0}
@media (prefers-color-scheme:dark){:root{--bg:#0f1411;--card:#19211c;--text:#e8efe9;--muted:#9aa99f;--ok:#22c55e;--ko:#f87171;--line:#2a352e}}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.45 system-ui,sans-serif}main{max-width:560px;margin:0 auto;padding:20px 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:14px}
.badge{font-weight:800;font-size:20px;color:${ok ? 'var(--ok)' : 'var(--ko)'}}.muted{color:var(--muted);font-size:14px}
table{width:100%;border-collapse:collapse}td{padding:6px 4px;border-bottom:1px solid var(--line)}td.n{text-align:right;font-weight:700}
code{word-break:break-all;font-size:12px}</style></head><body><main>
<div class="card"><div class="badge">${ok ? '✓ ' : '✗ '}${esc(statusText)}</div>
<p class="muted">${esc(v.valid ? 'Contenuto integro e firma di certificazione valida.' : v.reason)}</p></div>
<div class="card"><div class="muted">${esc(s.event.name)}${s.match.round ? ' · ' + esc(s.match.round) : ''}${s.match.court ? ' · Campo ' + esc(s.match.court) : ''}</div>
<table>${s.teams.map((t, i) => `<tr><td>${i === s.winner_team ? '<b>' + esc(t.name) + '</b>' : esc(t.name)}</td>${(s.score || []).map(x => `<td class="n">${x[i]}</td>`).join('')}</tr>`).join('')}</table>
<p class="muted">Firmato da ${s.signatures.length} giocatori${s.referee ? ' · arbitro: ' + esc(s.referee.name) : ''}<br>${s.certified_at ? 'Certificato il ' + esc(new Date(s.certified_at).toLocaleString('it-IT', { timeZone: 'Europe/Rome' })) : ''}</p></div>
${s.certificate ? `<div class="card muted">Impronta SHA-256<br><code>${esc(s.certificate.hash)}</code><br><br>Chiave ${esc(s.certificate.key_id)} · Ed25519</div>` : ''}
</main></body></html>`;
}

// ---------- Server HTTP ----------
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.yaml': 'text/yaml; charset=utf-8', '.json': 'application/json' };

function send(res, status, body, type = 'application/json') {
  res.writeHead(status, { 'content-type': type, 'access-control-allow-origin': '*', 'access-control-allow-headers': 'authorization, content-type', 'access-control-allow-methods': 'GET, POST, PUT, DELETE, OPTIONS', 'x-content-type-options': 'nosniff' });
  res.end(type === 'application/json' ? JSON.stringify(body) : body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0; const chunks = [];
    req.on('data', c => { size += c.length; if (size > MAX_BODY) { reject(new HttpError(413, 'too_large', 'richiesta troppo grande')); req.destroy(); } else chunks.push(c); });
    req.on('end', () => {
      if (!size) return resolve({});
      try { const b = JSON.parse(Buffer.concat(chunks)); resolve(b && typeof b === 'object' ? b : {}); }
      catch { reject(bad('JSON non valido')); }
    });
    req.on('error', reject);
  });
}

async function handle(req, res) {
  const url = new URL(req.url, 'http://x');
  const p = url.pathname;
  try {
    if (req.method === 'OPTIONS') return send(res, 204, '', 'text/plain');
    if (req.method === 'GET' && p.startsWith('/verify/')) {
      const s = db.scoresheets[decodeURIComponent(p.slice(8))];
      return s ? send(res, 200, verifyPage(s), MIME['.html']) : send(res, 404, 'Referto non trovato', 'text/plain; charset=utf-8');
    }
    if (req.method === 'GET' && !p.startsWith('/v1/')) {
      const rel = p === '/' ? 'index.html' : p === '/court/' || p === '/court' ? 'court.html' : p.slice(1);
      const file = path.join(PUBLIC_DIR, path.normalize(rel));
      if (!file.startsWith(PUBLIC_DIR) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) return send(res, 404, 'Non trovato', 'text/plain; charset=utf-8');
      return send(res, 200, fs.readFileSync(file), MIME[path.extname(file)] || 'application/octet-stream');
    }
    for (const r of routes) {
      if (r.method !== req.method) continue;
      const mm = r.re.exec(p);
      if (!mm) continue;
      const params = Object.fromEntries(Object.entries(mm.groups || {}).map(([k, v]) => [k, decodeURIComponent(v)]));
      const body = ['POST', 'PUT'].includes(req.method) ? await readBody(req) : {};
      return send(res, 200, await r.handler(req, params, body, url.searchParams));
    }
    throw new HttpError(404, 'not_found', 'endpoint inesistente');
  } catch (e) {
    if (e instanceof HttpError) return send(res, e.status, { error: { code: e.code, message: e.message, details: e.details } });
    console.error(e);
    send(res, 500, { error: { code: 'internal', message: 'errore interno' } });
  }
}

function start(port = +process.env.PORT || 8080) {
  loadDb(); loadKeys();
  const server = http.createServer(handle);
  return new Promise(r => server.listen(port, () => r(server)));
}

module.exports = { start, createPlatform: name => { loadDb(); loadKeys(); return createPlatform(name); }, canonical };

if (require.main === module) {
  const args = process.argv.slice(2);
  if (args[0] === 'create-platform') {
    const { platform, api_key } = module.exports.createPlatform(args.slice(1).join(' ') || 'Piattaforma');
    console.log(`Piattaforma creata: ${platform.name} (${platform.id})\nAPI key (mostrata una sola volta): ${api_key}`);
  } else {
    start().then(s => console.log(`Your Score in ascolto su http://localhost:${s.address().port}`));
  }
}
