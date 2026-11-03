#!/usr/bin/env python3
"""Refresh GamerXTube's data.json from YouTube using yt-dlp (no API key).

    pip install -U yt-dlp
    python3 scripts/refresh.py            # writes data.json next to index.html

What it does
  1. Featured channel (@ps5gameplaystation453): name, avatar, subscriber count,
     latest uploads and the most viewed of its recent uploads.
  2. For every game in GAMES: searches YouTube, drops Shorts / reuploads / spam /
     off-topic results, fetches full metadata for the strongest candidates and
     ranks them by views, likes, like/view ratio, recency and comment activity.
     The top 10 per game (max 2 per channel) get their top comments fetched
     (comment_sort=top) and the best short, clean one is kept.
Only values YouTube actually returns are stored; missing fields are omitted.
"""
import json, math, os, re, sys, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import yt_dlp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data.json')
CHANNEL = 'https://www.youtube.com/@ps5gameplaystation453'
PER_GAME = 10
WORKERS = 6

# Trending games (chosen 2026-11-03). Sources: Streams Charts "Most watched games on Twitch, last 7 days"
# (streamscharts.com/games?platform=twitch) and Steam Weekly Top Sellers Oct 27 - Nov 3 2026
# (store.steampowered.com/charts/topsellers/global/2026-10-27) + Steam Most Played.
GAMES = [
    {'id': 'lol', 'name': 'League of Legends', 'short': 'LoL', 'why': 'Twitch #2 (31.3M hours watched, last 7 days)',
     'queries': ['League of Legends gameplay', 'League of Legends best plays 2026', 'League of Legends highlights'], 'match': [r'league of legends', r'\blol\b', r'\bworlds\b', r'\blck\b', r'faker'],
     'exclude': r'wild rift|music video|\bft\.|cinematic|\bsong\b|arcane'},
    {'id': 'cs2', 'name': 'Counter-Strike 2', 'short': 'CS2', 'why': 'Twitch #3 (14.4M h) · Steam #1 most played',
     'queries': ['Counter-Strike 2 highlights', 'CS2 best plays 2026', 'CS2 gameplay'], 'match': [r'counter[- ]?strike', r'\bcs2\b', r'\bcs ?go\b', r'\bcs\b']},
    {'id': 'gtav', 'name': 'Grand Theft Auto V', 'short': 'GTA V', 'why': 'Twitch #4 (13.7M h) · GTA VI launches Nov 19',
     'queries': ['GTA 5 gameplay', 'GTA V best moments', 'GTA 5 RP 2026'], 'match': [r'\bgta\b', r'grand theft auto']},
    {'id': 'minecraft', 'name': 'Minecraft', 'short': 'Minecraft', 'why': 'Twitch #5 (13.5M h)',
     'queries': ['Minecraft gameplay', 'Minecraft best builds 2026', 'Minecraft hardcore'], 'match': [r'minecraft']},
    {'id': 'valorant', 'name': 'VALORANT', 'short': 'VALORANT', 'why': 'Twitch #6 (10.6M h)',
     'queries': ['Valorant highlights', 'Valorant best plays 2026', 'Valorant gameplay'], 'match': [r'valorant', r'\bvct\b']},
    {'id': 'dota2', 'name': 'Dota 2', 'short': 'Dota 2', 'why': 'Twitch #7 (9.4M h) · Steam #2 most played',
     'queries': ['Dota 2 highlights', 'Dota 2 best plays 2026', 'Dota 2 gameplay'], 'match': [r'\bdota\b']},
    {'id': 'fortnite', 'name': 'Fortnite', 'short': 'Fortnite', 'why': 'Twitch #8 (9.0M h)',
     'queries': ['Fortnite gameplay', 'Fortnite best moments 2026', 'Fortnite chapter'], 'match': [r'fortnite']},
    {'id': 'mw4', 'name': 'Call of Duty: Modern Warfare 4', 'short': 'CoD MW4', 'why': 'Twitch #9 (7.4M h) · Steam top sellers #2',
     'queries': ['Modern Warfare 4 gameplay', 'Call of Duty Modern Warfare 4', 'MW4 multiplayer gameplay'], 'match': [r'modern warfare (4|iv)\b', r'\bmw4\b', r'\bmwiv\b']},
    {'id': 'phantomblade', 'name': 'Phantom Blade Zero', 'short': 'Phantom Blade', 'why': 'Steam top sellers #1 · Twitch #12 (5.5M h)',
     'queries': ['Phantom Blade Zero gameplay', 'Phantom Blade Zero boss fight', 'Phantom Blade Zero review'], 'match': [r'phantom blade']},
    {'id': 'fc27', 'name': 'EA Sports FC 27', 'short': 'FC 27', 'why': 'Twitch #20 (3.3M h) · Steam top sellers #10 · big on PS5',
     'queries': ['EA FC 27 gameplay', 'FC 27 PS5 gameplay', 'EA Sports FC 27 best goals'], 'match': [r'\bfc ?27\b', r'fifa ?27', r'ea sports fc']},
]
TRENDING_SOURCES = [
    {'name': 'Streams Charts: most watched games on Twitch, last 7 days', 'url': 'https://streamscharts.com/games?platform=twitch', 'checked': '2026-11-03'},
    {'name': 'Steam Weekly Top Sellers, Oct 27 - Nov 3 2026', 'url': 'https://store.steampowered.com/charts/topsellers/global/2026-10-27', 'checked': '2026-11-03'},
    {'name': 'Steam Most Played', 'url': 'https://store.steampowered.com/charts/mostplayed', 'checked': '2026-11-03'},
]

SPAM = re.compile(r'(#shorts?\b|\bshorts?\b|free v-?bucks|v-?bucks generator|\bhack(s|ed)?\b|cheat(s|ing)?\b|aimbot|mod ?menu|giveaway|\bglitch\b.*\bmoney\b|money glitch|reupload|re-upload|\bnot mine\b|\bcredit to\b|\bsub ?4 ?sub\b|\bfree skins?\b|\bscam\b|\b(asmr)\b|\bunlock all\b|\bdownload (link|free)\b|\bapk\b|\bmobile\b.*\bdownload\b|\bfake\b)', re.I)
BAD_COMMENT = re.compile(r'((.)\2{5,}|like this comment|every like|for every like|\blikes? if\b|\binvest(ing)? in this\b|uninstall|\bcrap\b|f\*+|\bshit|\bfuck|https?://|www\.|\.com\b|\bsub(scribe)? to me\b|check (out )?my channel|\bmy channel\b|first!?$|\bwho.s (here|watching) in\b|telegram|whatsapp|\bcrypto\b|@\w+\s*$)', re.I)


def ydl(extra=None):
    o = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'ignoreerrors': True, 'socket_timeout': 30}
    o.update(extra or {})
    return yt_dlp.YoutubeDL(o)


def flat(url):
    with ydl({'extract_flat': 'in_playlist'}) as y:
        return y.extract_info(url, download=False) or {}


def full(vid, comments=False):
    extra = {}
    if comments:
        extra = {'getcomments': True, 'extractor_args': {'youtube': {'comment_sort': ['top'], 'max_comments': ['40', '40', '0', '0']}}}
    for attempt in range(3):
        try:
            with ydl(extra) as y:
                info = y.extract_info('https://www.youtube.com/watch?v=' + vid, download=False)
            if info:
                return info
        except Exception as e:  # noqa
            print('  retry', vid, e, file=sys.stderr)
        time.sleep(2 + attempt * 3)
    return None


def iso(d):
    return f'{d[:4]}-{d[4:6]}-{d[6:]}' if d and len(d) == 8 else None


def age_days(d):
    try:
        return max(1, (dt.date.today() - dt.date(int(d[:4]), int(d[4:6]), int(d[6:]))).days)
    except Exception:
        return None


def score(v):
    """Rank by reach (views), approval (likes and like/view ratio), discussion and freshness."""
    views, likes = v.get('view_count') or 0, v.get('like_count') or 0
    if views <= 0:
        return -1
    ratio = likes / views if likes else 0
    age = age_days(v.get('upload_date') or '') or 3650
    s = math.log10(views + 1) * 1.0 + math.log10(likes + 1) * 1.2 + min(ratio, 0.12) * 25
    s += math.log10((v.get('comment_count') or 0) + 1) * 0.3
    s += 1.6 * math.exp(-age / 365)          # fresher is better, but classics still rank
    return round(s, 3)


def pick_comment(info):
    best = None
    owner = info.get('channel_id')
    for c in info.get('comments') or []:
        if c.get('parent') not in (None, 'root'):
            continue
        t = re.sub(r'\s+', ' ', (c.get('text') or '')).strip()
        if len(t) < 18 or len(t) > 220 or BAD_COMMENT.search(t):
            continue
        if c.get('author_id') == owner:
            continue
        if len(t.split()) < 4 or sum(ch.isalpha() for ch in t) < len(t) * 0.5:
            continue
        lk = c.get('like_count') or 0
        if best is None or lk > best['likes']:
            best = {'text': t, 'author': c.get('author') or '', 'likes': lk}
    if best and not best['likes']:
        best.pop('likes')
    return best


def video_record(info, with_comment=True):
    r = {'id': info['id'], 'title': info.get('title'), 'channel': info.get('channel') or info.get('uploader'),
         'channel_url': info.get('channel_url') or info.get('uploader_url'), 'channel_handle': info.get('uploader_id'),
         'views': info.get('view_count'), 'likes': info.get('like_count'), 'comments': info.get('comment_count'),
         'uploaded': iso(info.get('upload_date')), 'duration': info.get('duration'),
         'thumb': f"https://i.ytimg.com/vi/{info['id']}/hqdefault.jpg"}
    if with_comment:
        c = pick_comment(info)
        if c:
            r['top_comment'] = c
    return {k: v for k, v in r.items() if v not in (None, '')}


def is_ok_candidate(e, game):
    t = (e.get('title') or '')
    url = e.get('url') or ''
    if '/shorts/' in url or SPAM.search(t):
        return False
    d = e.get('duration')
    if d is not None and d < 120:          # skip Shorts and tiny clips
        return False
    if e.get('live_status') in ('is_live', 'is_upcoming'):
        return False
    if game.get('exclude') and re.search(game['exclude'], t, re.I):
        return False
    return any(re.search(p, t, re.I) for p in game['match'])


def curate(game):
    print('==', game['name'], flush=True)
    cands = {}
    for q in game['queries']:
        res = flat('ytsearch40:' + q)
        for e in res.get('entries') or []:
            if e and e.get('id') and is_ok_candidate(e, game):
                cands.setdefault(e['id'], e)
    pool = sorted(cands.values(), key=lambda e: -(e.get('view_count') or 0))[:30]
    with ThreadPoolExecutor(WORKERS) as ex:
        infos = [i for i in ex.map(lambda e: full(e['id']), pool) if i]
    good = []
    for i in infos:
        if (i.get('duration') or 0) < 120 or i.get('was_live') and (i.get('duration') or 0) > 6 * 3600:
            continue
        if SPAM.search(i.get('title') or '') or SPAM.search((i.get('description') or '')[:300]) and 'reupload' in (i.get('description') or '').lower():
            continue
        if not i.get('view_count') or (i.get('like_count') is not None and i['view_count'] > 5000 and i['like_count'] / i['view_count'] < 0.002):
            continue  # likes hidden-ish or suspiciously low approval
        i['_score'] = score(i)
        good.append(i)
    good.sort(key=lambda i: -i['_score'])
    chosen, per_ch = [], {}
    for i in good:
        ch = i.get('channel_id')
        if per_ch.get(ch, 0) >= 2:
            continue
        per_ch[ch] = per_ch.get(ch, 0) + 1
        chosen.append(i)
        if len(chosen) == PER_GAME:
            break
    with ThreadPoolExecutor(WORKERS) as ex:
        detailed = list(ex.map(lambda i: full(i['id'], comments=True) or i, chosen))
    out = []
    for i, d in zip(chosen, detailed):
        rec = video_record(d)
        rec['score'] = i['_score']
        out.append(rec)
    print('   ', len(cands), 'candidates ->', len(good), 'clean ->', len(out), 'picked', flush=True)
    g = {k: game[k] for k in ('id', 'name', 'short', 'why')}
    g['queries'] = game['queries']
    g['videos'] = out
    return g


def channel():
    print('== featured channel', flush=True)
    res = flat(CHANNEL + '/videos')
    entries = [e for e in (res.get('entries') or []) if e and e.get('id')][:60]
    avatar = None
    for t in res.get('thumbnails') or []:
        if t.get('id') == 'avatar_uncropped' or (t.get('width') or 0) >= 176:
            avatar = t['url']
            break
    long_ones = [e for e in entries if (e.get('duration') or 0) > 60]   # skip Shorts
    latest = long_ones[:5]
    popular = [e for e in sorted(long_ones, key=lambda e: -(e.get('view_count') or 0)) if e not in latest][:5]
    ids = [e['id'] for e in latest + popular]
    with ThreadPoolExecutor(WORKERS) as ex:
        infos = [i for i in ex.map(lambda v: full(v, comments=True), ids) if i]
    vids = [video_record(i) for i in infos]
    for v in vids:
        v['tag'] = []
        if v['id'] in [e['id'] for e in latest]:
            v['tag'].append('latest')
        if v['id'] in [e['id'] for e in popular]:
            v['tag'].append('popular')
    return {
        'name': res.get('channel') or res.get('uploader'), 'handle': res.get('uploader_id'), 'url': CHANNEL,
        'channel_id': res.get('channel_id'), 'subscribers': res.get('channel_follower_count'),
        'avatar': avatar, 'description': (res.get('description') or '').strip().split('\n')[0][:160] or None,
        'videos': vids,
    }


def main():
    only = sys.argv[1:]
    data = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            data = json.load(f)
    if not only or 'channel' in only:
        data['channel'] = channel()
    old = {g['id']: g for g in data.get('games', [])}
    games = []
    for game in GAMES:
        if only and game['id'] not in only and old.get(game['id']):
            games.append(old[game['id']])
            continue
        games.append(curate(game))
    data['games'] = games
    data['trending_sources'] = TRENDING_SOURCES
    data['generated'] = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    data['method'] = ('yt-dlp search + metadata; Shorts (<2 min), live/upcoming, reuploads, spam and off-topic titles removed; '
                      'ranked by log(views), log(likes), like/view ratio, comment count and recency; max 2 videos per channel; '
                      'top comment = most-liked clean top-level comment from YouTube\'s "Top comments" sort.')
    with open(OUT, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
