'use strict';
// Demo: avvia Your Score, crea una piattaforma finta con un torneo e stampa i link dei tablet.
// Simula ciò che farebbe una piattaforma vera (OpenPlay, RAQT...) con poche chiamate API.
const http = require('node:http');
const { start, createPlatform } = require('../src/server');

const PORT = +process.env.PORT || 8080;

(async () => {
  const server = await start(PORT);
  const base = `http://localhost:${PORT}`;
  const { api_key } = createPlatform('Piattaforma demo');
  const call = (method, p, body) => fetch(base + p, { method, headers: { authorization: 'Bearer ' + api_key, 'content-type': 'application/json' }, body: body && JSON.stringify(body) }).then(r => r.json());

  // La "piattaforma" riceve i referti certificati qui.
  const hook = http.createServer((req, res) => {
    let b = ''; req.on('data', c => b += c);
    req.on('end', () => {
      const e = JSON.parse(b), s = e.data.scoresheet;
      console.log(`\n[piattaforma] ${e.type}: partita ${s.match.external_id} → ${s.teams[s.winner_team].name} ${s.score.map(x => x.join('-')).join(' ')}`);
      res.end('ok');
    });
  }).listen(PORT + 1);
  await call('POST', '/v1/webhooks', { url: `http://localhost:${PORT + 1}/yourscore`, events: ['*'] });

  await call('PUT', '/v1/events/DEMO-1', { name: 'Torneo Demo PickleballSpot', format: 'pickleball_11' });
  const p = (id, name) => ({ external_id: id, name });
  await call('POST', '/v1/events/DEMO-1/matches/batch', { matches: [
    { external_id: 'A1', court: '1', round: 'Girone A', scheduled_at: '2026-11-08T09:00', teams: [{ players: [p('u1', 'Mario Rossi'), p('u2', 'Luca Bianchi')] }, { players: [p('u3', 'Anna Verdi'), p('u4', 'Sara Neri')] }] },
    { external_id: 'A2', court: '1', round: 'Girone A', scheduled_at: '2026-11-08T09:30', teams: [{ players: [p('u5', 'Paolo Conti'), p('u6', 'Giulia Russo')] }, { players: [p('u7', 'Marco Gallo'), p('u8', 'Elena Costa')] }] },
    { external_id: 'B1', court: '2', round: 'Girone B', format: 'pickleball_11_bo3', teams: [{ name: 'I Leoni', players: [p('u9', 'Fabio Ricci'), p('u10', 'Davide Marino')] }, { name: 'Le Tigri', players: [p('u11', 'Chiara Greco'), p('u12', 'Marta Bruno')] }] },
    { external_id: 'P1', court: '3', round: 'Padel · Finale', format: 'padel_bo3_super', teams: [{ players: [p('u13', 'Andrea Romano'), p('u14', 'Simone Colombo')] }, { players: [p('u15', 'Laura Ferrari'), p('u16', 'Silvia Esposito')] }] },
  ] });
  const court1 = await call('POST', '/v1/events/DEMO-1/devices', { court: '1', label: 'Tablet campo 1' });
  const all = await call('POST', '/v1/events/DEMO-1/devices', { label: 'Arbitro (tutti i campi)' });

  console.log(`Your Score demo su ${base}\n`);
  console.log(`Tablet campo 1:          ${court1.tablet_url}`);
  console.log(`Tablet arbitro (tutti):  ${all.tablet_url}`);
  console.log(`\nAPI key della piattaforma demo: ${api_key}`);
  console.log(`Documentazione API: ${base}/openapi.yaml`);
})();
