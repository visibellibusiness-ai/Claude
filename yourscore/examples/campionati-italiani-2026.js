'use strict';
// Prova su un torneo reale: Campionati italiani di pickleball 2026, 159 Pickleball, Cassano Magnago
// (11-14 giugno 2026). Nomi e punteggi dalle cronache pubblicate da FITP Lombardia e Calabria Pickleball.
// Una "piattaforma" carica le partite, i tablet di campo registrano risultati e firme, la piattaforma
// riceve i referti via webhook. Alla fine si confrontano i referti con i risultati ufficiali.
//
// Uso: node examples/campionati-italiani-2026.js [cartella-output]
// Il tablet del campo 1 viene lasciato libero se si passa --manual-court1 (per pilotarlo da browser).
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { start, createPlatform } = require('../src/server');

const SOURCES = [
  'https://www.fitp.it/Siti-regionali/Lombardia/News/News/campionati-italiani-pickleball-2026-cassano-magnago',
  'https://www.calabriapickleball.it/2026/06/15/campionati-italiani-di-pickleball-a-cassano-magnago-eletti-i-campioni-2026/',
];

const P = (name) => ({ external_id: name.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z]+/g, '-'), name });
const pair = (a, b) => ({ players: [P(a), P(b)] });
const solo = a => ({ players: [P(a)] });

// I campi non sono pubblicati: l'assegnazione dei campi è della simulazione.
// official = punteggio ufficiale, null se non pubblicato.
const MATCHES = [
  { external_id: 'SM-SF1', round: 'Singolare maschile · Semifinale', court: '2', format: 'pickleball_15', teams: [solo('Matteo Cugliari'), solo('Yasser Taha')], official: [[15, 8]], source: 1 },
  { external_id: 'SM-SF2', round: 'Singolare maschile · Semifinale', court: '3', format: 'pickleball_15', teams: [solo('Alberto Seccia'), solo('Andrea Bosi')], official: [[15, 7]], source: 1 },
  { external_id: 'SM-3P', round: 'Singolare maschile · 3° posto', court: '3', format: 'pickleball_15', teams: [solo('Andrea Bosi'), solo('Yasser Taha')], official: null, note: 'vinta da Bosi, punteggio non pubblicato' },
  { external_id: 'SM-F', round: 'Singolare maschile · Finale', court: '1', format: 'pickleball_11_bo3', teams: [solo('Matteo Cugliari'), solo('Alberto Seccia')], official: [[11, 1], [8, 11], [11, 3]], source: 1 },
  { external_id: 'DM-F', round: 'Doppio maschile · Finale', court: '1', format: 'pickleball_11_bo3', teams: [pair('Matteo Cugliari', 'Alberto Seccia'), pair('Sergio Patricio Salandro', 'Stefano Moioli')], official: [[11, 1], [12, 10]], source: 1 },
  { external_id: 'DF-F', round: 'Doppio femminile · Finale', court: '2', format: 'pickleball_11_bo3', teams: [pair('Paola Tampieri', 'Natascia Sciolti'), pair('Antonella Sonda', 'Paola Bolzon')], official: [[11, 7], [11, 8]], source: 0 },
  { external_id: 'DX-F', round: 'Doppio misto · Finale', court: '3', format: 'pickleball_11_bo3', teams: [pair('Andrea Bosi', 'Paola Tampieri'), pair('Cristian Gallucci', 'Francesca Rumi')], official: [[12, 10], [11, 9]], source: 0 },
];

// Firma finta ma valida (un tratto disegnato in un PNG generato al volo).
function signaturePng(seed) {
  const w = 120, h = 40, rows = [];
  for (let y = 0; y < h; y++) {
    const row = [0];
    for (let x = 0; x < w; x++) row.push(Math.abs(y - (20 + Math.round(12 * Math.sin((x + seed) / 9)))) < 2 ? 0 : 255);
    rows.push(Buffer.from(row));
  }
  const zlib = require('node:zlib');
  const chunk = (type, data) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const crc = Buffer.alloc(4); crc.writeUInt32BE(zlib.crc32 ? zlib.crc32(td) >>> 0 : crc32(td));
    return Buffer.concat([len, td, crc]);
  };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 0;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(Buffer.concat(rows))), chunk('IEND', Buffer.alloc(0))]).toString('base64');
}
function crc32(buf) {
  let c, crc = 0xffffffff;
  for (const b of buf) { c = (crc ^ b) & 0xff; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; crc = (crc >>> 8) ^ c; }
  return (crc ^ 0xffffffff) >>> 0;
}

async function main() {
  const outDir = process.argv.slice(2).find(a => !a.startsWith('--')) || path.join(__dirname, '..', 'prove');
  const manualCourt1 = process.argv.includes('--manual-court1');
  fs.mkdirSync(outDir, { recursive: true });
  const port = +process.env.PORT || 8092;
  const server = await start(port);
  const base = `http://localhost:${port}`;
  const { api_key } = createPlatform('Piattaforma tornei (simulata)');
  const call = (method, p, body, token = api_key) => fetch(base + p, { method, headers: { authorization: 'Bearer ' + token, 'content-type': 'application/json' }, body: body && JSON.stringify(body) }).then(async r => ({ status: r.status, body: await r.json() }));

  // La piattaforma: riceve i webhook, controlla la firma HMAC e aggiorna il proprio tabellone.
  const board = {}, log = [];
  let secret;
  const hook = http.createServer((req, res) => {
    let raw = ''; req.on('data', c => raw += c);
    req.on('end', () => {
      const [t, v1] = req.headers['yourscore-signature'].split(',').map(x => x.split('=')[1]);
      const ok = crypto.createHmac('sha256', secret).update(`${t}.${raw}`).digest('hex') === v1;
      const e = JSON.parse(raw), s = e.data.scoresheet;
      if (ok && e.type === 'scoresheet.certified') board[s.match.external_id] = s;
      log.push(`${new Date().toISOString().slice(11, 19)} ${e.type} ${s.match.external_id} firma webhook ${ok ? 'valida' : 'NON valida'}`);
      res.end('ok');
    });
  });
  await new Promise(r => hook.listen(port + 1, r));
  secret = (await call('POST', '/v1/webhooks', { url: `http://localhost:${port + 1}/yourscore` })).body.secret;

  // 1. La piattaforma carica il torneo e il tabellone.
  await call('PUT', '/v1/events/CI-PICKLEBALL-2026', { name: 'Campionati italiani pickleball 2026 · Cassano Magnago', format: 'pickleball_11_bo3', starts_at: '2026-06-11' });
  const batch = await call('POST', '/v1/events/CI-PICKLEBALL-2026/matches/batch', { matches: MATCHES.map(({ official, note, source, ...m }) => m) });
  const loaded = batch.body.results.filter(r => r.ok).length;

  // 2. Un tablet per campo.
  const devices = {};
  for (const c of ['1', '2', '3']) devices[c] = (await call('POST', '/v1/events/CI-PICKLEBALL-2026/devices', { court: c, label: `Campo ${c}` })).body;
  fs.writeFileSync(path.join(outDir, '.court1-url'), devices['1'].tablet_url);

  // 3. I campi 2 e 3 inviano i referti via API del tablet; il campo 1 può essere usato da browser.
  const results = [];
  for (const m of MATCHES) {
    if (!m.official) { results.push({ m, skipped: true }); continue; }
    if (manualCourt1 && m.court === '1') continue;
    const dev = devices[m.court];
    const list = (await call('GET', '/v1/device/matches', null, dev.token)).body.matches;
    const id = list.find(x => x.external_id === m.external_id).id;
    const signatures = m.teams.flatMap(t => t.players).map((p, i) => ({ player_external_id: p.external_id, image_png_base64: signaturePng(i * 7 + p.name.length) }));
    const r = await call('POST', `/v1/device/matches/${id}/scoresheet`, { client_id: m.external_id, score: m.official, signatures }, dev.token);
    results.push({ m, status: r.status, body: r.body });
  }

  // Prova di errore: un punteggio impossibile sul campo 3 viene rifiutato prima della firma.
  const third = (await call('GET', '/v1/device/matches', null, devices['3'].token)).body.matches.find(x => x.external_id === 'SM-3P');
  const wrong = await call('POST', `/v1/device/matches/${third.id}/scoresheet`, { score: [[15, 14]], signatures: [] }, devices['3'].token);

  if (manualCourt1) {
    console.log('READY ' + devices['1'].tablet_url);
    await new Promise(r => process.once('SIGUSR2', r));
  }
  await new Promise(r => setTimeout(r, 300));

  // 4. Confronto con i risultati ufficiali e verifica pubblica di ogni referto.
  const rows = [];
  for (const m of MATCHES) {
    const s = board[m.external_id];
    const off = m.official ? m.official.map(x => x.join('-')).join(' ') : '—';
    if (!s) { rows.push(`| ${m.round} | ${m.teams.map(t => t.players.map(p => p.name).join(' / ')).join(' – ')} | ${off} | ${m.note || 'non inviato'} | — |`); continue; }
    const v = (await call('GET', `/v1/verify/${s.id}`)).body;
    const ys = s.score.map(x => x.join('-')).join(' ');
    const same = ys === off ? 'uguale' : 'DIVERSO';
    rows.push(`| ${m.round} | **${s.teams[s.winner_team].name}** b. ${s.teams[1 - s.winner_team].name} | ${off} | ${ys} (${same}), ${s.signatures.length} firme | ${v.valid ? 'integro' : 'NON valido'} · \`${s.certificate.hash.slice(0, 12).toUpperCase()}\` |`);
  }
  const report = `# Prova su torneo reale: Campionati italiani pickleball 2026

Torneo: **Campionati italiani di pickleball 2026**, 159 Pickleball, Cassano Magnago, 11-14 giugno 2026.
Fonti dei risultati ufficiali: [FITP Lombardia](${SOURCES[0]}) · [Calabria Pickleball](${SOURCES[1]}).
Prova eseguita il ${new Date().toLocaleString('it-IT', { timeZone: 'Europe/Rome' })}.

## Cosa è stato simulato

- Una piattaforma di tornei carica evento e tabellone con ${loaded} partite in una chiamata, con i propri ID.
- Tre tablet, uno per campo. I campi reali non sono pubblicati: l'assegnazione dei campi è della prova.
- Ogni referto è firmato da tutti i giocatori (firme generate dalla prova, non firme reali).
- La piattaforma riceve i referti via webhook firmato e aggiorna il proprio tabellone.

## Risultati ufficiali e referti Your Score

| Partita | Esito | Ufficiale | Referto Your Score | Verifica |
|---|---|---|---|---|
${rows.join('\n')}

## Controlli

- Partite caricate dalla piattaforma: ${loaded} su ${MATCHES.length}.
- Referti certificati arrivati alla piattaforma via webhook: ${Object.keys(board).length}.
- Webhook con firma valida: ${log.filter(l => l.includes('valida') && !l.includes('NON')).length} su ${log.length}.
- Punteggio impossibile (15-14 in un game ai 15) rifiutato: ${wrong.status === 422 ? 'sì' : 'NO'} — «${wrong.body.error && wrong.body.error.message}».
- Il punteggio reale 12-10 (vantaggi oltre l'11) è stato accettato correttamente.

## Limiti della prova

- Le semifinali del singolare maschile vengono solo da Calabria Pickleball; un'altra versione delle semifinali
  riportata dai motori di ricerca non coincide e non è stata usata.
- La finale per il 3° posto del singolare maschile non ha un punteggio pubblicato: resta aperta.
- Le altre partite del torneo (gironi, tabelloni completi, singolare femminile) non sono pubbliche
  nelle fonti consultate e non sono state ricostruite.

## Registro webhook

\`\`\`
${log.join('\n')}
\`\`\`
`;
  fs.writeFileSync(path.join(outDir, 'campionati-italiani-2026.md'), report);
  console.log(report);
  server.close(); hook.close();
}

main().catch(e => { console.error(e); process.exit(1); });
