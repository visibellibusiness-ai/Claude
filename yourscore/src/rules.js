'use strict';
// Regolamenti di punteggio. Un "set" è un game a punti (pickleball, badminton, ping pong)
// oppure un set a giochi (tennis, padel): in entrambi i casi il punteggio è [squadraA, squadraB].

const FORMATS = {
  pickleball_11:      { sport: 'pickleball', label: 'Pickleball, 1 game agli 11', unit: 'points', best_of: 1, to: 11, win_by: 2 },
  pickleball_15:      { sport: 'pickleball', label: 'Pickleball, 1 game ai 15', unit: 'points', best_of: 1, to: 15, win_by: 2 },
  pickleball_21:      { sport: 'pickleball', label: 'Pickleball, 1 game ai 21', unit: 'points', best_of: 1, to: 21, win_by: 2 },
  pickleball_11_bo3:  { sport: 'pickleball', label: 'Pickleball, 2 game su 3 agli 11', unit: 'points', best_of: 3, to: 11, win_by: 2 },
  padel_bo3:          { sport: 'padel', label: 'Padel, 2 set su 3', unit: 'games', best_of: 3, games: 6, final: 'set' },
  padel_bo3_super:    { sport: 'padel', label: 'Padel, 2 set su 3 con super tie-break', unit: 'games', best_of: 3, games: 6, final: 'super_tiebreak' },
  tennis_bo3:         { sport: 'tennis', label: 'Tennis, 2 set su 3', unit: 'games', best_of: 3, games: 6, final: 'set' },
  tennis_bo3_super:   { sport: 'tennis', label: 'Tennis, 2 set su 3 con super tie-break', unit: 'games', best_of: 3, games: 6, final: 'super_tiebreak' },
  tennis_1set:        { sport: 'tennis', label: 'Tennis, set unico', unit: 'games', best_of: 1, games: 6, final: 'set' },
  badminton_bo3:      { sport: 'badminton', label: 'Badminton, 2 game su 3 ai 21', unit: 'points', best_of: 3, to: 21, win_by: 2, cap: 30 },
  table_tennis_bo5:   { sport: 'table_tennis', label: 'Ping pong, 3 set su 5 agli 11', unit: 'points', best_of: 5, to: 11, win_by: 2 },
};

function checkPointsGame([a, b], to, winBy, cap) {
  const hi = Math.max(a, b), lo = Math.min(a, b);
  if (cap && hi === cap) return lo >= cap - winBy ? null : `si arriva al massimo a ${cap}`;
  if (hi < to) return `il game si vince arrivando a ${to}`;
  if (hi === to) return hi - lo >= winBy ? null : `servono ${winBy} punti di scarto`;
  // Oltre il punteggio base si va avanti solo ai vantaggi: lo scarto finale è esattamente winBy.
  return hi - lo === winBy ? null : `oltre ${to} si vince con esattamente ${winBy} punti di scarto`;
}

function checkGamesSet([a, b], games) {
  const hi = Math.max(a, b), lo = Math.min(a, b);
  if (hi === games && lo <= games - 2) return null;
  if (hi === games + 1 && (lo === games - 1 || lo === games)) return null;
  return `un set finisce ${games}-${games - 2} o meno, ${games + 1}-${games - 1} oppure ${games + 1}-${games} col tie-break`;
}

// Restituisce { ok, winner, sets_won } oppure { ok: false, error } con un messaggio in italiano.
function validateScore(formatId, sets) {
  const f = FORMATS[formatId];
  if (!f) return { ok: false, error: `regolamento sconosciuto: ${formatId}` };
  if (!Array.isArray(sets) || !sets.length) return { ok: false, error: 'inserisci il punteggio' };
  const need = Math.ceil(f.best_of / 2);
  const won = [0, 0];
  for (let i = 0; i < sets.length; i++) {
    const s = sets[i];
    if (!Array.isArray(s) || s.length !== 2 || !s.every(n => Number.isInteger(n) && n >= 0 && n <= 99)) {
      return { ok: false, error: `set ${i + 1}: punteggio non valido` };
    }
    if (won[0] === need || won[1] === need) return { ok: false, error: 'la partita era già finita prima di questo set' };
    if (s[0] === s[1]) return { ok: false, error: `set ${i + 1}: non può finire in parità` };
    const decider = f.best_of > 1 && i === f.best_of - 1;
    let err;
    if (f.unit === 'points') err = checkPointsGame(s, f.to, f.win_by, f.cap);
    else if (decider && f.final === 'super_tiebreak') err = checkPointsGame(s, 10, 2);
    else err = checkGamesSet(s, f.games);
    if (err) return { ok: false, error: `set ${i + 1}: ${err}` };
    won[s[0] > s[1] ? 0 : 1]++;
  }
  if (won[0] < need && won[1] < need) return { ok: false, error: 'la partita non è ancora finita' };
  return { ok: true, winner: won[0] === need ? 0 : 1, sets_won: won };
}

module.exports = { FORMATS, validateScore };
