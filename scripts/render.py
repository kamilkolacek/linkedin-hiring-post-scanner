#!/usr/bin/env python3
"""Render ranked posts (score.py output + drafts) into one self-contained HTML page.

Usage: python3 render.py ranked.json out.html

Each post may carry `draft_note` (connection note, <=300 chars) and `draft_dm`
(longer DM). Exits non-zero if any draft_note is over 300 chars, so the skill
fixes it before publishing.
"""
import json
import sys
from datetime import datetime

NOTE_LIMIT = 300

TEMPLATE = r"""<title>Hiring Post Radar</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap">
<style>
/* Layout: one ranked column of outreach cards under a compact run summary; ledger-green accent, score shown as a points ledger out of 100. */
:root {
  --bg: #f5f7f6; --surface: #ffffff; --ink: #18211e; --muted: #5b6862; --line: #dbe2df;
  --accent: #1d6b4f; --accent-soft: #e2f0ea;
  --hm: #1d6b4f; --rec: #3b5bb5; --team: #7a5a1f; --warn: #b3261e;
  --seg1: #1d6b4f; --seg2: #4f9a7c; --seg3: #3b5bb5; --seg4: #a07a2c; --seg5: #8a96a0;
  --f-display: "Space Grotesk", "Helvetica Neue", Arial, sans-serif;
  --f-body: "IBM Plex Sans", -apple-system, "Segoe UI", sans-serif;
  --f-mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0f1513; --surface: #161e1b; --ink: #e6ece9; --muted: #98a6a0; --line: #2a3531;
  --accent: #5cc59a; --accent-soft: #1b2f27;
  --hm: #5cc59a; --rec: #8fa8f0; --team: #d8b062; --warn: #f2867e;
  --seg1: #5cc59a; --seg2: #3c8a6b; --seg3: #8fa8f0; --seg4: #d8b062; --seg5: #6c7a74;
  color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #0f1513; --surface: #161e1b; --ink: #e6ece9; --muted: #98a6a0; --line: #2a3531;
  --accent: #5cc59a; --accent-soft: #1b2f27;
  --hm: #5cc59a; --rec: #8fa8f0; --team: #d8b062; --warn: #f2867e;
  --seg1: #5cc59a; --seg2: #3c8a6b; --seg3: #8fa8f0; --seg4: #d8b062; --seg5: #6c7a74;
  color-scheme: dark; }
body { background: var(--bg); color: var(--ink); font-family: var(--f-body); font-size: 15px; line-height: 1.5; }
.wrap { max-width: 860px; margin: 0 auto; padding-block: 28px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 20px; }
h1 { font-family: var(--f-display); font-weight: 600; font-size: 1.75rem; margin: 0; text-wrap: balance; letter-spacing: -0.01em; }
.sub { color: var(--muted); margin: 4px 0 0; }
.summary { display: flex; flex-wrap: wrap; gap: 8px 20px; font-size: 0.85rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.summary b { color: var(--ink); font-weight: 600; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font: 500 0.8rem var(--f-body); border: 1px solid var(--line); background: var(--surface); color: var(--ink);
  border-radius: 999px; padding: 5px 12px; cursor: pointer; }
.chip[aria-pressed="true"] { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.chip:focus-visible, button:focus-visible, textarea:focus-visible, a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.list { display: grid; gap: 14px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 18px; display: grid; gap: 12px; min-width: 0; }
.top { display: grid; grid-template-columns: auto 1fr auto; gap: 14px; align-items: start; }
.rank { font: 500 0.8rem var(--f-mono); color: var(--muted); padding-top: 3px; }
.who { min-width: 0; }
.who h2 { font: 600 1.05rem var(--f-display); margin: 0; }
.who h2 a { color: inherit; text-decoration: none; }
.who h2 a:hover { text-decoration: underline; }
.headline { color: var(--muted); font-size: 0.85rem; overflow-wrap: anywhere; }
.score { text-align: right; font-variant-numeric: tabular-nums; }
.score .n { font: 600 1.5rem var(--f-display); line-height: 1; }
.score .of { font: 0.75rem var(--f-mono); color: var(--muted); }
.meta { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 0.85rem; align-items: center; }
.pill { font: 600 0.7rem var(--f-body); text-transform: uppercase; letter-spacing: 0.06em; padding: 3px 8px; border-radius: 4px; border: 1px solid currentColor; }
.pill.loc { color: var(--muted); } .pill.loc.south_bay { color: var(--accent); } .pill.loc.unknown { color: var(--warn); }
.pill.hiring_manager { color: var(--hm); } .pill.recruiter { color: var(--rec); } .pill.team_member { color: var(--team); }
.role { font-weight: 600; }
.dim { color: var(--muted); }
.excerpt { margin: 0; color: var(--ink); font-size: 0.9rem; border-left: 2px solid var(--line); padding-left: 12px; overflow-wrap: anywhere; }
.ledger { display: grid; gap: 6px; }
.bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: var(--line); }
.bar span { display: block; height: 100%; }
.legend { display: flex; flex-wrap: wrap; gap: 4px 14px; font: 0.75rem var(--f-mono); color: var(--muted); font-variant-numeric: tabular-nums; }
.legend i { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 5px; vertical-align: 0; }
.drafts { display: grid; gap: 10px; }
.draft { display: grid; gap: 6px; }
.draft-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.label { font: 600 0.72rem var(--f-body); text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); }
.count { font: 0.75rem var(--f-mono); color: var(--muted); font-variant-numeric: tabular-nums; }
.count.over { color: var(--warn); font-weight: 500; }
textarea { font: 0.9rem/1.5 var(--f-body); color: var(--ink); background: var(--bg); border: 1px solid var(--line);
  border-radius: 6px; padding: 10px; resize: vertical; width: 100%; box-sizing: border-box; min-height: 92px; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; }
.btn { font: 500 0.82rem var(--f-body); border-radius: 6px; padding: 7px 12px; cursor: pointer; border: 1px solid var(--line); background: var(--surface); color: var(--ink); text-decoration: none; }
.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--surface); }
.repo { font-size: 0.85rem; color: var(--muted); }
.repo a { color: var(--accent); }
.empty { background: var(--surface); border: 1px dashed var(--line); border-radius: 10px; padding: 24px; display: grid; gap: 8px; }
.empty h2 { font: 600 1.1rem var(--f-display); margin: 0; }
.leads { display: grid; gap: 10px; }
.leads > h2 { font: 600 1.15rem var(--f-display); margin: 8px 0 0; }
.leads > p { margin: 0; }
.lead { background: var(--surface); border: 1px solid var(--line); border-left: 3px solid var(--seg4); border-radius: 8px; padding: 14px 16px; display: grid; gap: 6px; min-width: 0; }
.lead .lh { display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: baseline; }
.lead .lh b { font: 600 0.98rem var(--f-display); }
.lead .lh a { color: inherit; }
.pill.kind { color: var(--team); }
.lead .act { font-size: 0.88rem; }
.lead .act span { font: 600 0.72rem var(--f-body); text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); margin-right: 6px; }
details { font-size: 0.85rem; color: var(--muted); }
details ul { padding-left: 18px; margin: 8px 0 0; }
details code { font-family: var(--f-mono); font-size: 0.78rem; overflow-wrap: anywhere; }
.note { font-size: 0.8rem; color: var(--muted); }
@media (max-width: 520px) { .top { grid-template-columns: 1fr auto; } .rank { grid-column: 1 / -1; padding: 0; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>

<div class="wrap">
  <header>
    <h1>Hiring Post Radar</h1>
    <p class="sub" id="sub"></p>
  </header>
  <div class="summary" id="summary"></div>
  <div class="filters" id="filters" role="group" aria-label="Filter by who posted"></div>
  <div class="list" id="list"></div>
  <section class="leads" id="leads" aria-labelledby="leads-h" hidden>
    <h2 id="leads-h">Leads to watch</h2>
    <p class="dim">Not job posts yet. Departures and reorgs at target companies that often open a finance role in the weeks after.</p>
    <div class="list" id="leads-list"></div>
  </section>
  <details id="runlog"><summary>Searches run and posts filtered out</summary><ul id="runlog-list"></ul></details>
  <p class="note">Drafts are never sent from here. Edit, copy, and send them yourself on LinkedIn. Your edits stay in this browser only.</p>
</div>

<script type="application/json" id="data">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById('data').textContent);
  const LIMIT = __LIMIT__;
  const REL = { hiring_manager: 'Hiring manager', recruiter: 'Recruiter', team_member: 'Team member' };
  const SEGS = [['company','Company','--seg1',30],['role_fit','Role fit','--seg2',40],['proximity','Poster','--seg3',15],['freshness','Fresh','--seg4',5],['location','Location','--seg5',10]];
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  const el = (t, cls, txt) => { const e = document.createElement(t); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
  const link = (href, txt, cls) => { const a = el('a', cls, txt); if (/^https:\/\//.test(href || '')) { a.href = href; a.target = '_blank'; a.rel = 'noopener'; } return a; };

  const when = D.scanned_at ? new Date(D.scanned_at) : null;
  document.getElementById('sub').textContent =
    'LinkedIn posts from the last 24 hours by recruiters, hiring managers and team members at your target companies' +
    (when ? ' · scanned ' + when.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '');

  const posts = D.posts || [];
  const counts = posts.reduce((m, p) => (m[p.relation] = (m[p.relation] || 0) + 1, m), {});
  const sum = document.getElementById('summary');
  [['Posts ranked', posts.length], ['Hiring managers', counts.hiring_manager || 0], ['Recruiters', counts.recruiter || 0],
   ['Companies searched', (D.searches || []).length]].forEach(([k, v]) => {
    const s = el('span'); s.append(el('b', null, String(v)), ' ' + k); sum.append(s);
  });

  let filter = 'all';
  const fwrap = document.getElementById('filters');
  [['all', 'All'], ['hiring_manager', 'Hiring managers'], ['recruiter', 'Recruiters'], ['team_member', 'Team members']].forEach(([k, label]) => {
    const b = el('button', 'chip', label); b.type = 'button'; b.id = 'f-' + k;
    b.setAttribute('aria-pressed', String(k === filter));
    b.onclick = () => { filter = k; fwrap.querySelectorAll('.chip').forEach(c => c.setAttribute('aria-pressed', String(c === b))); render(); };
    fwrap.append(b);
  });

  function copy(btn, ta) {
    const done = () => { const t = btn.textContent; btn.textContent = 'Copied'; setTimeout(() => btn.textContent = t, 1400); };
    const fallback = () => { ta.focus(); ta.select(); btn.textContent = 'Press ⌘C to copy'; setTimeout(() => btn.textContent = 'Copy', 2200); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(ta.value).then(done, fallback); else fallback();
  }

  function draftBlock(p, kind, label, limit) {
    const box = el('div', 'draft');
    const head = el('div', 'draft-head');
    const id = 'd-' + kind + '-' + p.rank;
    const lab = el('label', 'label', label); lab.htmlFor = id;
    const cnt = el('span', 'count');
    head.append(lab, cnt);
    const ta = el('textarea'); ta.id = id;
    const key = 'draft:' + (p.post_url || p.rank) + ':' + kind;
    ta.value = store.get(key) ?? (p[kind] || '');
    const upd = () => { const n = ta.value.length; cnt.textContent = limit ? n + ' / ' + limit + ' chars' : n + ' chars'; cnt.classList.toggle('over', !!limit && n > limit); };
    ta.addEventListener('input', () => { store.set(key, ta.value); upd(); }); upd();
    const actions = el('div', 'actions');
    const b = el('button', 'btn primary', 'Copy'); b.type = 'button'; b.onclick = () => copy(b, ta);
    actions.append(b);
    box.append(head, ta, actions);
    return box;
  }

  function card(p) {
    const c = el('article', 'card');
    const top = el('div', 'top');
    const who = el('div', 'who');
    const h = el('h2'); h.append(link(p.author_url, p.author_name || 'Unknown poster'));
    who.append(h, el('div', 'headline', p.author_headline || ''));
    const sc = el('div', 'score'); sc.append(el('div', 'n', String(Math.round(p.score))), el('div', 'of', '/ 100'));
    top.append(el('div', 'rank', '#' + p.rank), who, sc);

    const meta = el('div', 'meta');
    meta.append(el('span', 'pill ' + p.relation, REL[p.relation] || p.relation));
    if (p.role_title) meta.append(el('span', 'role', p.role_title));
    meta.append(el('span', 'dim', p.company + (p.location ? ' · ' + p.location : '')));
    const TIER = { south_bay: 'South Bay', bay_area: 'Bay Area', remote: 'Remote', unknown: 'Location not stated' };
    if (p.location_tier) meta.append(el('span', 'pill loc ' + p.location_tier, TIER[p.location_tier] || p.location_tier));
    const age = Number(p.posted_hours_ago);
    meta.append(el('span', 'dim', age < 1 ? 'under 1h ago' : Math.round(age) + 'h ago'));
    if (p.post_url) meta.append(link(p.post_url, 'Open post ↗'));

    const ex = el('p', 'excerpt', (p.text || '').slice(0, 320) + ((p.text || '').length > 320 ? '…' : ''));

    const led = el('div', 'ledger');
    const bar = el('div', 'bar'); bar.setAttribute('role', 'img');
    bar.setAttribute('aria-label', 'Score breakdown: ' + SEGS.map(s => s[1] + ' ' + (p.breakdown[s[0]] || 0) + ' of ' + s[3]).join(', '));
    const leg = el('div', 'legend');
    SEGS.forEach(([k, name, tok, max]) => {
      const v = p.breakdown[k] || 0;
      const s = el('span'); s.style.width = v + '%'; s.style.background = 'var(' + tok + ')'; bar.append(s);
      const l = el('span'); const i = el('i'); i.style.background = 'var(' + tok + ')'; l.append(i, name + ' ' + v + '/' + max); leg.append(l);
    });
    led.append(bar, leg);

    const drafts = el('div', 'drafts');
    drafts.append(draftBlock(p, 'draft_note', 'Connection note', LIMIT));
    if (p.draft_dm) drafts.append(draftBlock(p, 'draft_dm', 'Message (after connecting)', 0));
    if (p.suggested_repo) {
      const r = el('div', 'repo'); r.append('Repo cited: ', link(p.suggested_repo.url, p.suggested_repo.name), ' · ' + p.suggested_repo.pitch);
      drafts.append(r);
    }
    c.append(top, meta, ex, led, drafts);
    return c;
  }

  function render() {
    const list = document.getElementById('list'); list.replaceChildren();
    const shown = posts.filter(p => filter === 'all' || p.relation === filter);
    if (!shown.length) {
      const e = el('div', 'empty');
      e.append(el('h2', null, posts.length ? 'No posts in this filter' : 'No matching hiring posts in the last 24 hours'),
        el('p', 'dim', posts.length ? 'Choose another filter above.' : 'The searches below ran and found nothing that matched. Add companies to the tracker or config.json and run the scan again.'));
      list.append(e); return;
    }
    shown.forEach(p => list.append(card(p)));
  }
  render();

  const KIND = { departure: 'Departure', layoff: 'Layoff', reorg: 'Reorg', new_leader: 'New leader', other: 'Signal' };
  const leads = D.leads || [];
  if (leads.length) {
    const ll = document.getElementById('leads-list');
    leads.forEach(L => {
      const c = el('article', 'lead');
      const h = el('div', 'lh');
      h.append(el('span', 'pill kind', KIND[L.kind] || 'Signal'));
      const b = el('b'); b.append(L.person ? link(L.person_url, L.person) : document.createTextNode(L.company || '')); h.append(b);
      h.append(el('span', 'dim', [L.company, L.location].filter(Boolean).join(' · ')));
      if (L.posted_hours_ago != null) h.append(el('span', 'dim', Math.round(Number(L.posted_hours_ago)) + 'h ago'));
      if (L.source_url) h.append(link(L.source_url, 'Source ↗'));
      c.append(h);
      if (L.headline) c.append(el('div', 'headline', L.headline));
      if (L.note) c.append(el('p', 'excerpt', L.note));
      if (L.suggested_action) { const a = el('div', 'act'); a.append(el('span', null, 'Next step'), L.suggested_action); c.append(a); }
      ll.append(c);
    });
    document.getElementById('leads').hidden = false;
  }

  const log = document.getElementById('runlog-list');
  (D.searches || []).forEach(s => {
    const li = el('li'); li.append((s.company || '') + ': ' + (s.result_count ?? '?') + ' results ');
    if (s.status && s.status !== 'ok') li.append('(' + s.status + ') ');
    log.append(li);
  });
  (D.dropped || []).forEach(d => log.append(el('li', null, 'Filtered: ' + (d.author_name || '?') + ' (' + (d.company || '?') + ') — ' + d.reason)));
  if (!log.children.length) document.getElementById('runlog').hidden = true;
})();
</script>
"""


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: render.py ranked.json out.html")
    data = json.load(open(sys.argv[1]))
    data.setdefault("scanned_at", datetime.now().isoformat(timespec="minutes"))
    over = [p for p in data.get("posts", []) if len(p.get("draft_note") or "") > NOTE_LIMIT]
    missing = [p for p in data.get("posts", []) if not p.get("draft_note")]
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__DATA__", blob).replace("__LIMIT__", str(NOTE_LIMIT))
    with open(sys.argv[2], "w") as f:
        f.write(html)
    for p in over:
        print(f"ERROR: rank {p['rank']} draft_note is {len(p['draft_note'])} chars (> {NOTE_LIMIT})", file=sys.stderr)
    for p in missing:
        print(f"WARN: rank {p.get('rank')} has no draft_note", file=sys.stderr)
    print(f"wrote {sys.argv[2]} with {len(data.get('posts', []))} posts", file=sys.stderr)
    sys.exit(1 if over else 0)


if __name__ == "__main__":
    main()
