/*
 * On-device ComicVine client — JavaScript port of the fetch + ranking logic in
 * src/ingest/comicvine.py. Runs in React Native (direct HTTPS from the phone).
 *
 * ComicVine is used instead of League of Comic Geeks because LCG has no public
 * API — the Python uses a scraper that is too fragile to embed in a shipped app.
 * The franchise/publisher ranking below is the same one the Python falls back to
 * when LCG is unavailable, so ordering stays consistent.
 */

const BASE_URL = 'https://comicvine.gamespot.com/api';
const HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  Accept: 'application/json',
  Referer: 'https://comicvine.gamespot.com',
};

const TIER_1 = ['dc comics', 'dc', 'marvel comics', 'marvel'];
const TIER_2 = ['image comics', 'image', 'dark horse comics', 'dark horse',
  'idw publishing', 'idw', 'boom! studios', 'boom studios',
  'dynamite entertainment', 'dynamite', 'valiant', 'aftershock', 'titan'];

const MARQUEE_SCORES = {
  'amazing spider-man': 100, 'ultimate spider-man': 90, 'spider-man': 92, 'spider man': 92,
  'uncanny x-men': 96, 'x-men': 95, 'ultimate x-men': 84, wolverine: 90, deadpool: 88,
  avengers: 90, venom: 86, daredevil: 80, 'fantastic four': 82, 'captain america': 84,
  'iron man': 84, thor: 82, hulk: 82, 'moon knight': 70, punisher: 72, magneto: 70,
  storm: 68, 'star wars': 86,
  batman: 100, 'detective comics': 92, superman: 96, 'action comics': 90, 'wonder woman': 88,
  'justice league': 90, flash: 80, 'green lantern': 80, aquaman: 70, nightwing: 74, robin: 68,
  'harley quinn': 80, joker: 82, absolute: 88, supergirl: 66, 'teen titans': 70,
  'green arrow': 66, catwoman: 66, shazam: 60, 'poison ivy': 58,
  'teenage mutant ninja turtles': 76, tmnt: 76, transformers: 74, godzilla: 70,
  'the walking dead': 72, saga: 78, invincible: 76, spawn: 72, hellboy: 66,
};
const MARQUEE_KEY_THRESHOLD = 70;

const REPRINT_KEYWORDS = ['omnibus', 'compendium', 'hardcover', 'trade paperback', 'tpb',
  'collected', 'complete', '2nd printing', 'second printing', 'anniversary edition', "director's cut"];

const DC_NAMES = ['dc comics', 'dc', 'vertigo', 'black label'];
const MARVEL_NAMES = ['marvel comics', 'marvel', 'marvel universe'];
const IMAGE_NAMES = ['image comics', 'image'];
const DH_NAMES = ['dark horse comics', 'dark horse'];
const IDW_NAMES = ['idw publishing', 'idw'];

// ---- date helpers ---------------------------------------------------------
function upcomingWednesday(today = new Date()) {
  const d = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const daysUntilWed = (2 - ((d.getDay() + 6) % 7) + 7) % 7; // JS getDay: Sun=0
  d.setDate(d.getDate() + daysUntilWed);
  return d;
}
function iso(d) { return d.toISOString().slice(0, 10); }
function weekRange(today = new Date()) {
  const wed = upcomingWednesday(today);
  const tue = new Date(wed); tue.setDate(tue.getDate() + 6);
  return [iso(wed), iso(tue)];
}
export function formatStreetDate(d = upcomingWednesday()) {
  return d.toLocaleDateString('en-US', { month: 'long', day: '2-digit', year: 'numeric' });
}

// ---- low-level request ----------------------------------------------------
async function cvGet(apiKey, endpoint, params) {
  const qs = new URLSearchParams({ ...params, api_key: apiKey, format: 'json' });
  const res = await fetch(`${BASE_URL}/${endpoint}/?${qs.toString()}`, { headers: HEADERS });
  if (!res.ok) throw new Error(`ComicVine ${endpoint} → HTTP ${res.status}`);
  return res.json();
}

// ---- getters --------------------------------------------------------------
export function getTitle(issue) {
  const vol = (issue.volume && issue.volume.name) || 'Unknown';
  const num = issue.issue_number || '';
  const name = issue.name || '';
  if (name) return num ? `${vol}: ${name} #${num}` : `${vol}: ${name}`;
  return num ? `${vol} #${num}` : vol;
}
export function getCoverUrl(issue) {
  const img = issue.image || {};
  return img.original_url || img.super_url || img.medium_url || null;
}
export function getPublisher(issue) {
  return (issue.publisher && issue.publisher.name) ||
    (issue._volPublisher || '');
}

// ---- ranking --------------------------------------------------------------
function marqueeScore(issue) {
  const name = (issue.name || '').toLowerCase();
  const volName = ((issue.volume && issue.volume.name) || '').toLowerCase();
  const hay = `${volName} ${name}`;
  let best = 0;
  for (const [k, w] of Object.entries(MARQUEE_SCORES)) if (hay.includes(k) && w > best) best = w;
  return best;
}
function seriesScore(issue) {
  const pub = (getPublisher(issue) || '').toLowerCase().trim();
  let tier = 0;
  if (TIER_1.some((t) => pub.includes(t))) tier = 2;
  else if (TIER_2.some((t) => pub.includes(t))) tier = 1;
  const count = issue._countOfIssues || 0;
  const num = (issue.issue_number || '').trim();
  const firstBonus = num === '1' ? 40 : 0;
  return marqueeScore(issue) * 1000 + tier * 100 + Math.min(count, 200) + firstBonus;
}
function isReprint(issue) {
  const name = (issue.name || '').toLowerCase();
  const vol = ((issue.volume && issue.volume.name) || '').toLowerCase();
  return REPRINT_KEYWORDS.some((kw) => name.includes(kw) || vol.includes(kw));
}
function pubBucket(pub) {
  const p = (pub || '').toLowerCase().trim();
  if (DC_NAMES.some((n) => p.includes(n))) return 'dc';
  if (MARVEL_NAMES.some((n) => p.includes(n))) return 'marvel';
  if (IMAGE_NAMES.some((n) => p.includes(n))) return 'image';
  if (DH_NAMES.some((n) => p.includes(n))) return 'dark_horse';
  if (IDW_NAMES.some((n) => p.includes(n))) return 'idw';
  return 'other';
}

// Resolve publisher via the volume endpoint when the issue lacks it. Cached
// per volume for the life of the run.
async function warmVolumes(apiKey, issues) {
  const cache = {};
  const ids = [...new Set(issues.map((i) => i.volume && i.volume.id).filter(Boolean))];
  await Promise.all(ids.map(async (vid) => {
    try {
      const d = await cvGet(apiKey, `volume/4050-${vid}`, { field_list: 'id,publisher,count_of_issues' });
      cache[vid] = d.results || {};
    } catch { cache[vid] = {}; }
  }));
  for (const it of issues) {
    const v = cache[it.volume && it.volume.id];
    if (v) {
      it._volPublisher = (v.publisher && v.publisher.name) || it._volPublisher || '';
      it._countOfIssues = v.count_of_issues || 0;
    }
  }
}

// ---- public API -----------------------------------------------------------

/**
 * Fetch, rank, and shape a full week of comics for the renderer.
 * Returns { streetDate, top, collectors } — `picks` is chosen by the user.
 */
export async function fetchComicsWeek(apiKey, { limit = 10 } = {}) {
  if (!apiKey) throw new Error('No ComicVine API key set. Add it in Settings.');
  const [wed, tue] = weekRange();
  const data = await cvGet(apiKey, 'issues', {
    filter: `store_date:${wed}|${tue}`,
    field_list: 'id,name,issue_number,volume,image,store_date,publisher',
    sort: 'store_date:desc',
    limit: 100,
    offset: 0,
  });

  const seen = new Set();
  const candidates = [];
  for (const issue of data.results || []) {
    if (!issue.id || seen.has(issue.id) || isReprint(issue)) continue;
    seen.add(issue.id);
    candidates.push(issue);
  }
  await warmVolumes(apiKey, candidates);

  // Drop anything outside the five color-coded publishers, matching the Python.
  const covered = candidates.filter((i) => pubBucket(getPublisher(i)) !== 'other');
  covered.sort((a, b) => seriesScore(b) - seriesScore(a));

  const top = covered.slice(0, limit).map(shape);
  const topTitles = new Set(top.map((t) => t.title));
  const collectors = scanCollectors(covered).filter((c) => !topTitles.has(c.title));
  const finalCollectors = (collectors.length ? collectors : scanCollectors(covered)).slice(0, 4);

  return { streetDate: formatStreetDate(), top, collectors: finalCollectors };
}

function shape(issue) {
  return { title: getTitle(issue), coverUrl: getCoverUrl(issue), publisher: getPublisher(issue) };
}

function scanCollectors(issues) {
  const CHECKS = [
    [['1:100'], '1:100 RATIO'], [['1:50'], '1:50 RATIO'], [['1:25'], '1:25 RATIO'],
    [['1:10'], '1:10 RATIO'], [['foil variant', 'foil cover', 'gold foil'], 'FOIL VARIANT'],
    [['virgin variant', 'virgin cover'], 'VIRGIN COVER'], [['connecting'], 'CONNECTING CVR'],
    [['sketch variant'], 'SKETCH COVER'], [['facsimile'], 'FACSIMILE'],
    [['first appearance', '1st appearance'], 'FIRST APPEARANCE'], [['anniversary'], 'ANNIVERSARY'],
  ];
  const out = []; const seen = new Set();
  for (const issue of issues) {
    const title = getTitle(issue); const tl = title.toLowerCase();
    const num = (issue.issue_number || '').trim();
    let reason = null;
    for (const [kws, label] of CHECKS) if (kws.some((k) => tl.includes(k))) { reason = label; break; }
    if (!reason && /^\d+$/.test(num) && +num >= 50 && +num % 50 === 0) reason = 'MILESTONE';
    if (!reason && num === '1' && marqueeScore(issue) > MARQUEE_KEY_THRESHOLD) reason = '#1 ISSUE';
    if (reason && !seen.has(title)) {
      seen.add(title);
      out.push({ title, coverUrl: getCoverUrl(issue), publisher: getPublisher(issue), reason });
    }
  }
  return out;
}
