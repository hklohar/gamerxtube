(() => {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = n => n >= 1e9 ? (n/1e9).toFixed(1).replace(/\.0$/,'')+'B' : n >= 1e6 ? (n/1e6).toFixed(1).replace(/\.0$/,'')+'M' : n >= 1e3 ? (n/1e3).toFixed(1).replace(/\.0$/,'')+'K' : String(n);
  const dur = s => { if (!s) return ''; const h = Math.floor(s/3600), m = Math.floor(s%3600/60), x = String(s%60).padStart(2,'0'); return h ? `${h}:${String(m).padStart(2,'0')}:${x}` : `${m}:${x}`; };
  const ago = iso => {
    if (!iso) return '';
    const d = (Date.now() - new Date(iso + 'T12:00:00Z')) / 864e5;
    if (d < 1) return 'today'; if (d < 2) return '1 day ago'; if (d < 31) return `${Math.floor(d)} days ago`;
    if (d < 365) { const m = Math.floor(d/30.4); return `${m} month${m>1?'s':''} ago`; }
    const y = Math.floor(d/365); return `${y} year${y>1?'s':''} ago`;
  };
  const fmtDate = iso => iso ? new Date(iso + 'T12:00:00Z').toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric', timeZone:'UTC'}) : '';
  let DATA = null, active = 'all', query = '';
  const SITE = 'https://hklohar.github.io/gamerxtube/';
  const SHARE_TEXT = 'GamerXTube: the 10 best YouTube videos for every trending game, ranked by views, likes and top comments';
  const vlink = id => SITE + '#v=' + encodeURIComponent(id);
  let toastT;
  function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), 1800); }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); }
    catch (e) { const a = document.createElement('textarea'); a.value = text; a.setAttribute('readonly', ''); a.style.position = 'fixed'; a.style.opacity = '0'; document.body.appendChild(a); a.select(); try { document.execCommand('copy'); } catch (_) {} a.remove(); }
    toast('Copied!');
  }
  async function share(data) {
    if (navigator.share) { try { await navigator.share(data); return; } catch (e) { if (e && e.name === 'AbortError') return; } }
    copy(data.url);
  }

  function card(v, i, extraTag) {
    const s = [];
    if (v.views != null) s.push(`<span title="${v.views.toLocaleString()} views">👁 ${num(v.views)} view${v.views === 1 ? "" : "s"}</span>`);
    if (v.likes != null) s.push(`<span class="lk" title="${v.likes.toLocaleString()} likes">♥ ${num(v.likes)}</span>`);
    if (v.uploaded) s.push(`<span title="${fmtDate(v.uploaded)}">${ago(v.uploaded)}</span>`);
    const c = v.top_comment;
    const cm = c ? `<blockquote class="cmt"><q>${esc(c.text)}</q><span class="who">${esc(c.author)}${c.likes ? ` · ♥ ${num(c.likes)}` : ''} · top comment</span></blockquote>` : '';
    const url = `https://www.youtube.com/watch?v=${encodeURIComponent(v.id)}`;
    return `<article class="card" data-id="${esc(v.id)}">
      <button class="player" type="button" data-id="${esc(v.id)}" aria-label="Play ${esc(v.title)}">
        <img src="${esc(v.thumb)}" alt="" loading="lazy" decoding="async" width="480" height="360">
        <span class="play" aria-hidden="true"></span>
        ${i != null ? `<span class="pos">#${i+1}</span>` : ''}
        ${extraTag ? `<span class="tag">${esc(extraTag)}</span>` : ''}
        ${v.duration ? `<span class="dur">${dur(v.duration)}</span>` : ''}
      </button>
      <div class="body">
        <h3 class="title"><a href="${url}" target="_blank" rel="noopener">${esc(v.title)}</a></h3>
        <div class="by">${v.channel_url ? `<a href="${esc(v.channel_url)}" target="_blank" rel="noopener">${esc(v.channel)}</a>` : esc(v.channel)}</div>
        <div class="stats">${s.join('')}</div>
        ${cm}
        <div class="actions"><a class="yt" href="${url}" target="_blank" rel="noopener">Open on YouTube ↗</a><button type="button" class="vshare" data-id="${esc(v.id)}" aria-label="Share this video">↗ Share</button></div>
      </div>
    </article>`;
  }

  function hero(ch) {
    const vids = ch.videos || [];
    $('#hero').innerHTML = `
      <div class="hero-head">
        ${ch.avatar ? `<img class="avatar" src="${esc(ch.avatar)}" alt="${esc(ch.name)} avatar" width="72" height="72">` : ''}
        <div>
          <div class="kicker">Featured channel</div>
          <h1>${esc(ch.name)}</h1>
          <div class="meta">${esc(ch.handle || '')}${ch.subscribers != null ? ` · ${num(ch.subscribers)} subscribers` : ''}${vids.length ? ` · PS5 gameplay` : ''}</div>
        </div>
      </div>
      ${ch.description ? `<p class="desc">${esc(ch.description)}</p>` : ''}
      <a class="sub" href="${esc(ch.url)}?sub_confirmation=1" target="_blank" rel="noopener">▶ Subscribe</a><a class="sub ghost" href="${esc(ch.url)}/videos" target="_blank" rel="noopener">Visit channel ↗</a>
      <div class="rail">${vids.map(v => card(v, null, (v.tag || []).includes('popular') ? 'popular' : 'latest')).join('')}</div>`;
  }

  function chips() {
    const g = DATA.games;
    $('#chips').innerHTML = [`<button class="chip" data-g="all" aria-pressed="true">🔥 All games</button>`]
      .concat(g.map(x => `<button class="chip" data-g="${esc(x.id)}" aria-pressed="false">${esc(x.short || x.name)}</button>`)).join('');
  }

  const hay = (v, g) => [v.title, v.channel, g.name, g.short, v.top_comment && v.top_comment.text].join(' ').toLowerCase();

  function render() {
    const q = query.trim().toLowerCase();
    let shown = 0;
    const html = DATA.games.map((g, gi) => {
      if (active !== 'all' && g.id !== active) return '';
      const vids = g.videos.map((v, i) => [v, i]).filter(([v]) => !q || q.split(/\s+/).every(t => hay(v, g).includes(t)));
      if (!vids.length) return '';
      shown += vids.length;
      return `<section class="game" id="g-${esc(g.id)}">
        <div class="game-head"><span class="rank">#${gi+1}</span><h2>${esc(g.name)}</h2><span class="why">Trending: ${esc(g.why)} · top ${g.videos.length} videos, ranked</span></div>
        <div class="grid">${vids.map(([v, i]) => card(v, i)).join('')}</div>
      </section>`;
    }).join('');
    $('#games').innerHTML = html || `<p class="empty">No videos match “${esc(query)}”.</p>`;
    $('#status').textContent = q ? `${shown} video${shown === 1 ? '' : 's'} match “${query.trim()}”` : '';
  }

  function play(btn) {
    document.querySelectorAll('.player iframe').forEach(f => { const b = f.parentElement; f.remove(); b.classList.remove('on'); b.querySelectorAll('img,.play,.dur,.pos,.tag').forEach(e => e.hidden = false); });
    const id = btn.dataset.id;
    const f = document.createElement('iframe');
    f.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&playsinline=1&rel=0&modestbranding=1`;
    f.title = 'YouTube video player';
    f.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
    f.allowFullscreen = true;
    f.referrerPolicy = 'strict-origin-when-cross-origin';
    btn.querySelectorAll('img,.play,.dur,.pos,.tag').forEach(e => e.hidden = true);
    btn.classList.add('on');
    btn.appendChild(f);
    if (location.hash !== '#v=' + id) history.replaceState(null, '', '#v=' + encodeURIComponent(id));
  }

  function findVideo(id) {
    for (const g of DATA.games) { const v = g.videos.find(x => x.id === id); if (v) return {v, g}; }
    const v = (DATA.channel.videos || []).find(x => x.id === id);
    return v ? {v, g: null} : null;
  }

  function openDeepLink() {
    const h = decodeURIComponent(location.hash.slice(1));
    if (!h) return;
    const id = h.startsWith('v=') ? h.slice(2) : h;
    if (!/^[\w-]{6,20}$/.test(id)) return;
    const hit = findVideo(id);
    if (!hit) return;
    let card;
    if (hit.g) {
      query = ''; $('#q').value = '';
      active = hit.g.id;
      document.querySelectorAll('.chip').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.g === active)));
      render();
      card = document.querySelector(`#games .card[data-id="${CSS.escape(id)}"]`);
    } else {
      card = document.querySelector(`#hero .card[data-id="${CSS.escape(id)}"]`);
    }
    if (!card) return;
    document.querySelectorAll('.card.hl').forEach(c => c.classList.remove('hl'));
    card.classList.add('hl');
    card.scrollIntoView({block: 'center', inline: 'center'});
    play(card.querySelector('.player'));
  }

  function setupShareBar() {
    const u = encodeURIComponent(SITE), t = encodeURIComponent(SHARE_TEXT);
    $('#shareX').href = `https://x.com/intent/post?text=${t}&url=${u}`;
    $('#shareReddit').href = `https://www.reddit.com/submit?url=${u}&title=${encodeURIComponent('GamerXTube: the 10 best YouTube videos for every trending game')}`;
    $('#shareWA').href = `https://wa.me/?text=${encodeURIComponent(SHARE_TEXT + ' ' + SITE)}`;
    $('#shareFB').href = `https://www.facebook.com/sharer/sharer.php?u=${u}`;
    if (navigator.share) { const n = $('#shareNative'); n.hidden = false; n.addEventListener('click', () => share({title: 'GamerXTube', text: SHARE_TEXT, url: SITE})); }
    $('#shareCopy').addEventListener('click', () => copy(SITE));
  }

  document.addEventListener('click', e => {
    const vs = e.target.closest('.vshare');
    if (vs) { const hit = findVideo(vs.dataset.id); share({title: hit ? hit.v.title + ' · GamerXTube' : 'GamerXTube', text: hit ? `${hit.v.title} (${hit.v.channel})` : SHARE_TEXT, url: vlink(vs.dataset.id)}); return; }
    const p = e.target.closest('.player');
    if (p && !p.classList.contains('on')) { e.preventDefault(); play(p); return; }
    const c = e.target.closest('.chip');
    if (c) {
      active = c.dataset.g;
      document.querySelectorAll('.chip').forEach(x => x.setAttribute('aria-pressed', String(x === c)));
      c.scrollIntoView({inline: 'center', block: 'nearest', behavior: 'smooth'});
      render();
      const top = $('#chips').offsetTop - 50;
      if (window.scrollY > top) window.scrollTo({top, behavior: 'smooth'});
    }
  });
  let t;
  $('#q').addEventListener('input', e => { clearTimeout(t); t = setTimeout(() => { query = e.target.value; render(); }, 120); });

  fetch('data.json', {cache: 'no-cache'}).then(r => r.json()).then(d => {
    DATA = d;
    hero(d.channel);
    chips();
    render();
    $('#srcs').innerHTML = (d.trending_sources || []).map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a>`).join(', ');
    setupShareBar();
    openDeepLink();
    window.addEventListener('hashchange', openDeepLink);
    $('#gen').textContent = d.generated ? new Date(d.generated).toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'}) : '';
  }).catch(() => { $('#status').textContent = 'Could not load data.json'; });
})();
