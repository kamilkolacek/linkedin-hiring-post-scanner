// Paste as the `text` of a javascript_tool call on a LinkedIn content-search results page.
// LinkedIn's results scroll inside <main>, not the window, so window.scrollTo / get_page_text
// alone only see the first ~6 posts. This scrolls <main> until no new posts load (max 8 rounds),
// keeps posts that mention an opening, and returns a compact list. Full post bodies stay in
// window.__hits for follow-up calls (they are lost when the tab navigates).
// URLs with query strings are masked because the tool blocks output containing them.
const m = document.querySelector('main');
if (!m || /captcha|unusual activity|security verification/i.test(document.body.innerText.slice(0, 3000))) {
  'BLOCKED or no results container';
} else {
  const cnt = () => m.innerText.split(/Feed post/).length - 1;
  let prev = -1, n = cnt(), i = 0;
  while (n !== prev && i < 8) { prev = n; m.scrollTop = m.scrollHeight; await new Promise(r => setTimeout(r, 2500)); n = cnt(); i++; }
  const ch = m.innerText.split(/Feed post/).slice(1);
  window.__hits = ch.map(c => {
    const L = c.trim().split('\n').map(s => s.trim()).filter(s => s && s !== '•' && !/^• (1st|2nd|3rd\+)$/.test(s));
    return { head: L.slice(0, 3).join(' | '), body: L.slice(3).join(' ').replace(/https?:\/\/\S*\?\S*/g, '<url>') };
  }).filter(p => /hiring|opening|open role|join (my|our|the) team|apply (here|now|below)|we're looking|looking for (a|an) |#hiring|job/i.test(p.body));
  // Output is truncated at roughly 1,000 characters, so keep each line short.
  'total ' + ch.length + ' hits ' + window.__hits.length + '\n' +
    window.__hits.map((p, k) => k + '. ' + p.head.slice(0, 65) + ' :: ' + p.body.slice(0, 100)).join('\n');
}
// Follow-up on the same page: window.__hits[k].body.slice(0, 900) to read one post in full.
