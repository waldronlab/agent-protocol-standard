(function () {
  'use strict';

  // Federation entry point. Falls back to this repository if the registry is unreachable.
  var REGISTRY_URL = 'https://raw.githubusercontent.com/waldronlab/agent-protocol-standard/main/registry.yaml';
  var FALLBACK_REGISTRIES = [{
    name: 'waldronlab/agent-protocols',
    index_url: 'https://raw.githubusercontent.com/waldronlab/agent-protocols/main/PROTOCOLS.yaml'
  }];
  var FACETS = ['category', 'status', 'type', 'registry', 'reviewed'];

  var $ = function (id) { return document.getElementById(id); };
  var all = [];
  var state = { q: '', category: new Set(), status: new Set(), type: new Set(), registry: new Set(), reviewed: new Set(), tags: new Set(), sort: 'relevance' };

  // ---- loading ----
  // raw.githubusercontent.com caches for ~5 minutes; a fresh query string bypasses stale copies.
  function fetchYaml(url, bust) {
    return fetch(url + (bust ? '?_=' + Date.now() : ''), { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error(url + ' → HTTP ' + r.status);
      return r.text();
    }).then(function (t) { return jsyaml.load(t, { schema: jsyaml.CORE_SCHEMA }); });
  }

  function deps(v) {
    return arr(v).map(function (d) {
      if (d && typeof d === 'object') return { name: str(d.name), repository: str(d.repository), version: str(d.version) };
      return { name: str(d), repository: '', version: '' };
    }).filter(function (d) { return d.name; });
  }
  function depLabel(d) { return d.name + (d.version ? ' v' + d.version : '') + (d.repository ? ' (' + d.repository + ')' : ''); }

  // Citations are a DOI (10.x/...) or a PubMed ID (PMID:123); each needs its own resolver.
  function citationUrl(c) {
    c = str(c).trim();
    var m = /^PMID:\s*(\d+)$/i.exec(c);
    if (m) return 'https://pubmed.ncbi.nlm.nih.gov/' + m[1] + '/';
    if (/^10\.\d{4,9}\//.test(c)) return 'https://doi.org/' + c.replace(/^https?:\/\/(dx\.)?doi\.org\//i, '');
    return '';
  }

  function arr(v) { return Array.isArray(v) ? v : (v == null ? [] : [v]); }
  function str(v) { return v == null ? '' : String(v); }

  function normalize(p, registryName) {
    var reviews = arr(p.reviews);
    // An approval counts only for the version it reviewed; a later release is not approved by it.
    var version = str(p.version);
    var approved = reviews.some(function (r) {
      return r && r.status === 'approved' && str(r.protocol_version) === version;
    });
    var n = {
      raw: p, registry: registryName,
      name: str(p.name), description: str(p.description).replace(/\s+/g, ' ').trim(),
      version: str(p.version), status: str(p.status) || 'unknown', type: str(p.type) || 'unknown',
      category: str(p.category) || 'Uncategorized', date: str(p.date),
      tags: arr(p.tags).map(str), packages: arr(p.key_packages).map(str),
      authors: arr(p.authors).map(function (a) { return a && a.name ? str(a.name) : str(a); }),
      reviews: reviews, reviewed: approved ? 'Approved (current version)' : 'Not approved for current version',
      url: safeUrl(p.protocol_url)
    };
    n.haystack = {
      name: n.name.toLowerCase(), tags: n.tags.join(' ').toLowerCase(),
      desc: n.description.toLowerCase(),
      other: [n.category, n.packages.join(' '), n.authors.join(' '), deps(p.protocols_used).map(function (d) { return d.name + ' ' + d.repository; }).join(' '),
        arr(p.upstream_repositories).join(' '), arr(p.database_urls).join(' ')].join(' ').toLowerCase()
    };
    return n;
  }

  // Only allow http(s) links: index data comes from third-party registries.
  function safeUrl(u) {
    try { var x = new URL(str(u)); return /^https?:$/.test(x.protocol) ? x.href : ''; } catch (e) { return ''; }
  }
  function viewUrl(u) { // raw URL → GitHub HTML view
    var m = /^https:\/\/raw\.githubusercontent\.com\/([^/]+)\/([^/]+)\/([^/]+)\/(.+)$/.exec(u);
    return m ? 'https://github.com/' + m[1] + '/' + m[2] + '/blob/' + m[3] + '/' + m[4] : u;
  }

  var meta = {};   // registry name -> generated_at of its PROTOCOLS.yaml
  var lastLoad = 0;

  function load(bust) {
    var notices = $('notices');
    notices.textContent = '';
    function notice(msg) { var d = document.createElement('div'); d.className = 'notice'; d.textContent = msg; notices.appendChild(d); }

    return fetchYaml(REGISTRY_URL, bust).then(function (reg) { return arr(reg && reg.registries); })
      .catch(function (e) { notice('Could not load the federation registry; showing the default registry only. (' + e.message + ')'); return FALLBACK_REGISTRIES; })
      .then(function (regs) {
        return Promise.all(regs.map(function (r) {
          var rname = str(r.name);
          var url = safeUrl(r.index_url);
          if (!url) { notice('Registry ' + rname + ' has no valid index_url.'); return []; }
          return fetchYaml(url, bust).then(function (idx) {
            meta[rname] = str(idx && idx.generated_at);
            return arr(idx && idx.protocols).map(function (p) { return normalize(p || {}, rname); });
          }).catch(function (e) { notice('Could not load registry ' + rname + ': ' + e.message); return []; });
        }));
      }).then(function (lists) {
        var fresh = [].concat.apply([], lists).filter(function (p) { return p.name; });
        if (fresh.length || !all.length) all = fresh; // keep the last good data if a refresh fails entirely
        lastLoad = Date.now();
      });
  }

  function showSynced() {
    var gen = Object.keys(meta).map(function (k) { return meta[k]; }).filter(Boolean).sort().pop();
    var t = new Date(lastLoad).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    $('synced').textContent = lastLoad ? 'Synced ' + t + (gen ? ' · index built ' + gen.replace('T', ' ').replace(/:\d\dZ$/, ' UTC') : '') : '';
  }

  function refresh() {
    var b = $('refresh'); b.disabled = true; b.textContent = 'Refreshing…';
    return load(true).then(function () { render(); showSynced(); }).then(function () { b.disabled = false; b.textContent = 'Refresh'; });
  }

  // ---- search ----
  function tokens(q) { return q.toLowerCase().split(/\s+/).filter(Boolean); }

  function score(p, toks) {
    if (!toks.length) return 1;
    var s = 0;
    for (var i = 0; i < toks.length; i++) {
      var t = toks[i], h = p.haystack, ts = 0;
      if (h.name.indexOf(t) >= 0) ts += 10;
      if (h.tags.indexOf(t) >= 0) ts += 6;
      if (h.desc.indexOf(t) >= 0) ts += 3;
      if (h.other.indexOf(t) >= 0) ts += 1;
      if (!ts) return 0; // every term must match somewhere (AND)
      s += ts;
    }
    return s;
  }

  function matchesFilters(p, skip) {
    for (var i = 0; i < FACETS.length; i++) {
      var f = FACETS[i];
      if (f === skip) continue;
      if (state[f].size && !state[f].has(p[f])) return false;
    }
    if (skip !== 'tags') {
      var ok = true;
      state.tags.forEach(function (t) { if (p.tags.indexOf(t) < 0) ok = false; });
      if (!ok) return false;
    }
    return true;
  }

  // ---- rendering ----
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function highlight(parent, text, toks) {
    if (!toks.length || !text) { parent.appendChild(document.createTextNode(text)); return; }
    var re = new RegExp('(' + toks.map(function (t) { return t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') + ')', 'ig');
    text.split(re).forEach(function (part, i) {
      if (i % 2) parent.appendChild(el('mark', null, part)); else if (part) parent.appendChild(document.createTextNode(part));
    });
  }

  function renderFacet(facet, base, toks) {
    var counts = {};
    base.forEach(function (p) {
      if (!matchesFilters(p, facet) || !score(p, toks)) return;
      counts[p[facet]] = (counts[p[facet]] || 0) + 1;
    });
    state[facet].forEach(function (v) { if (!(v in counts)) counts[v] = 0; });
    var box = $('f-' + facet); box.textContent = '';
    Object.keys(counts).sort().forEach(function (v) {
      var lab = el('label'), cb = document.createElement('input');
      cb.type = 'checkbox'; cb.checked = state[facet].has(v);
      cb.addEventListener('change', function () { toggle(state[facet], v, cb.checked); });
      lab.appendChild(cb); lab.appendChild(el('span', null, v)); lab.appendChild(el('span', 'n', String(counts[v])));
      box.appendChild(lab);
    });
  }

  function renderTags(toks) {
    var counts = {};
    all.forEach(function (p) {
      if (!matchesFilters(p, 'tags') || !score(p, toks)) return;
      p.tags.forEach(function (t) { counts[t] = (counts[t] || 0) + 1; });
    });
    state.tags.forEach(function (t) { if (!(t in counts)) counts[t] = 0; });
    var box = $('f-tags'); box.textContent = '';
    Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a] || a.localeCompare(b); }).forEach(function (t) {
      var b = el('button', 'tag', t + ' ' + counts[t]); b.type = 'button';
      b.setAttribute('aria-pressed', state.tags.has(t));
      b.addEventListener('click', function () { toggle(state.tags, t, !state.tags.has(t)); });
      box.appendChild(b);
    });
  }

  function card(p, toks) {
    var c = el('article', 'card');
    var h = el('h3');
    if (p.url) { var a = el('a'); a.href = viewUrl(p.url); a.rel = 'noopener'; highlight(a, p.name, toks); h.appendChild(a); }
    else highlight(h, p.name, toks);
    c.appendChild(h);
    var d = el('p'); highlight(d, p.description, toks); c.appendChild(d);

    var meta = el('div', 'meta');
    meta.appendChild(el('span', 'badge ' + p.status, p.status));
    if (p.reviewed === 'Approved (current version)') meta.appendChild(el('span', 'badge rev', '✓ Reviewed'));
    [p.type, p.category, p.version && 'v' + p.version, p.date, p.registry].forEach(function (x) { if (x) meta.appendChild(el('span', null, x)); });
    c.appendChild(meta);

    if (p.tags.length) {
      var tg = el('div', 'tagcloud'); tg.style.marginTop = '6px';
      p.tags.forEach(function (t) {
        var b = el('button', 'tag', t); b.type = 'button';
        b.addEventListener('click', function () { toggle(state.tags, t, true); });
        tg.appendChild(b);
      });
      c.appendChild(tg);
    }

    var det = el('details'); det.appendChild(el('summary', null, 'Details'));
    var dl = el('dl');
    function row(k, v, link) {
      if (!v || (Array.isArray(v) && !v.length)) return;
      dl.appendChild(el('dt', null, k));
      var dd = el('dd');
      arr(v).forEach(function (x, i) {
        if (i) dd.appendChild(document.createTextNode(', '));
        var u = link ? safeUrl(link(x)) : '';
        if (u) { var a = el('a', null, x); a.href = u; a.rel = 'noopener'; dd.appendChild(a); }
        else dd.appendChild(document.createTextNode(x));
      });
      dl.appendChild(dd);
    }
    var raw = p.raw;
    row('Authors', p.authors);
    row('Key packages', p.packages);
    row('Uses protocols', deps(raw.protocols_used).map(depLabel));
    row('Upstream repos', arr(raw.upstream_repositories).map(str), function (x) { return x; });
    row('Databases', arr(raw.database_urls).map(str), function (x) { return x; });
    row('Protocol citation', str(raw.protocol_citation), citationUrl);
    row('Method origin', str(raw.method_origin_citation), citationUrl);
    row('Collection DOI', str(raw.collection_doi), citationUrl);
    row('Artifact DOI', str(raw.artifact_doi), citationUrl);
    row('License', str(raw.license));
    row('Reviews', p.reviews.map(function (r) { return (r.name || '?') + ' — ' + (r.status || '?') + (r.protocol_version ? ' for v' + r.protocol_version : '') + (r.date ? ' (' + r.date + ')' : ''); }));
    row('Raw protocol (for agents)', p.url ? [p.url] : [], function (x) { return x; });
    det.appendChild(dl); c.appendChild(det);
    return c;
  }

  function render() {
    var toks = tokens(state.q);
    FACETS.forEach(function (f) { renderFacet(f, all, toks); });
    renderTags(toks);

    var rows = all.map(function (p) { return { p: p, s: score(p, toks) }; })
      .filter(function (r) { return r.s && matchesFilters(r.p); });
    var sort = state.sort;
    rows.sort(function (a, b) {
      if (sort === 'name' || (sort === 'relevance' && !toks.length)) return a.p.name.localeCompare(b.p.name);
      if (sort === 'date') return b.p.date.localeCompare(a.p.date) || a.p.name.localeCompare(b.p.name);
      return b.s - a.s || a.p.name.localeCompare(b.p.name);
    });

    $('count').textContent = rows.length + ' of ' + all.length + ' protocols';
    var regs = new Set(all.map(function (p) { return p.registry; })).size;
    var rev = all.filter(function (p) { return p.reviewed === 'Approved (current version)'; }).length;
    $('stats').innerHTML = '';
    [[all.length, 'protocols'], [regs, regs === 1 ? 'registry' : 'registries'], [rev, 'reviewed']].forEach(function (x) {
      var s = el('span'); s.appendChild(el('b', null, String(x[0]))); s.appendChild(document.createTextNode(' ' + x[1])); $('stats').appendChild(s);
    });
    var box = $('results'); box.textContent = '';
    if (!rows.length) box.appendChild(el('div', 'empty', all.length ? 'No protocols match. Try fewer terms or clear filters.' : 'No protocols loaded.'));
    rows.forEach(function (r) { box.appendChild(card(r.p, toks)); });
  }

  // ---- state <-> URL hash ----
  function toggle(set, v, on) { if (on) set.add(v); else set.delete(v); sync(); render(); }

  function sync() {
    var u = new URLSearchParams();
    if (state.q) u.set('q', state.q);
    FACETS.concat('tags').forEach(function (f) { state[f].forEach(function (v) { u.append(f, v); }); });
    if (state.sort !== 'relevance') u.set('sort', state.sort);
    var h = u.toString();
    history.replaceState(null, '', h ? '#' + h : location.pathname + location.search);
  }

  function readHash() {
    var u = new URLSearchParams(location.hash.slice(1));
    state.q = u.get('q') || '';
    FACETS.concat('tags').forEach(function (f) { state[f] = new Set(u.getAll(f)); });
    state.sort = u.get('sort') || 'relevance';
    $('q').value = state.q; $('sort').value = state.sort;
  }


  // Decorative terminal line: types `agent run <protocol>` for each loaded protocol in turn.
  function startTicker() {
    var tk = $('tk');
    if (!tk || matchMedia('(prefers-reduced-motion: reduce)').matches || !all.length) return;
    var names = all.map(function (p) { return p.name; });
    var i = 0, n = 0, phase = 'type', text = '';
    function tick() {
      var delay = 40;
      if (document.hidden) { setTimeout(tick, 1000); return; }
      if (phase === 'type') {
        text = 'agent run ' + names[i % names.length];
        n++; tk.textContent = text.slice(0, n);
        if (n >= text.length) { phase = 'hold'; delay = 500; }
      } else if (phase === 'hold') {
        tk.textContent = text + ' ';
        var ok = document.createElement('span'); ok.className = 'ok'; ok.textContent = '\u2713'; tk.appendChild(ok);
        phase = 'erase'; delay = 1500;
      } else {
        n = text.length; tk.textContent = ''; phase = 'type'; i++; n = 0; delay = 350;
      }
      setTimeout(tick, delay);
    }
    tk.textContent = '';
    tick();
  }

  function init() {
    $('q').addEventListener('input', function (e) { state.q = e.target.value; sync(); render(); });
    $('sort').addEventListener('change', function (e) { state.sort = e.target.value; sync(); render(); });
    $('clear').addEventListener('click', function () {
      state.q = ''; FACETS.concat('tags').forEach(function (f) { state[f] = new Set(); });
      $('q').value = ''; sync(); render();
    });
    window.addEventListener('hashchange', function () { readHash(); render(); });
    $('count').textContent = 'Loading…';
    for (var i = 0; i < 3; i++) $('results').appendChild(el('div', 'skeleton'));
    function currentTheme() {
      var t = document.documentElement.dataset.theme;
      return t || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    }
    function showTheme() {
      var t = currentTheme();
      $('theme-light').setAttribute('aria-pressed', String(t === 'light'));
      $('theme-dark').setAttribute('aria-pressed', String(t === 'dark'));
    }
    ['light', 'dark'].forEach(function (t) {
      $('theme-' + t).addEventListener('click', function () {
        document.documentElement.dataset.theme = t;
        try { localStorage.setItem('theme', t); } catch (e) {}
        showTheme();
      });
    });
    showTheme();
    document.addEventListener('keydown', function (e) {
      if (e.key === '/' && !/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName)) { e.preventDefault(); $('q').focus(); }
    });
    readHash();
    load(false).then(function () { render(); showSynced(); startTicker(); });
    $('refresh').addEventListener('click', refresh);
    // Stay in sync with GitHub: re-pull every 5 minutes, and when the tab regains focus after a while.
    setInterval(function () { if (!document.hidden) refresh(); }, 5 * 60 * 1000);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden && Date.now() - lastLoad > 2 * 60 * 1000) refresh();
    });
  }

  if (typeof module !== 'undefined') module.exports = { normalize: normalize, score: score };
  else init();
})();
