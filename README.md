# GamerXTube

A curated gaming-video site: **https://hklohar.github.io/gamerxtube/**

- **Featured channel:** [GamingStation (@ps5gameplaystation453)](https://www.youtube.com/@ps5gameplaystation453), showing its latest and most viewed full-length uploads (Shorts are skipped).
- **Trending games:** 10 games picked on 2026-11-03 from the [Streams Charts Twitch 7-day ranking](https://streamscharts.com/games?platform=twitch) and the [Steam weekly top sellers](https://store.steampowered.com/charts/topsellers/global/2026-10-27) / [most played](https://store.steampowered.com/charts/mostplayed) charts.
- **Each game** has the 10 best YouTube videos, ranked by views, likes, like/view ratio, comment count and recency (max 2 per channel). Shorts, reuploads, spam and off-topic results are removed. Each card shows the most-liked clean comment from YouTube's "Top comments".

Plain HTML/CSS/JS with no build step. Videos play in a click-to-load `youtube-nocookie.com` embed.

## Refresh the data

```bash
pip install -U yt-dlp
python3 scripts/refresh.py              # everything
python3 scripts/refresh.py channel fc27 # only the channel + one game (others kept)
```

No API key is needed. Every number and comment in `data.json` comes straight from YouTube via yt-dlp. A field YouTube didn't return is omitted, never guessed.

Videos belong to their creators. © 2026 Harish Lohar · hklohar@gmail.com
