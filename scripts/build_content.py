#!/usr/bin/env python3
"""Render the Projects and Writing blocks of index.html from data/.

  data/site.json   written by hand: the projects and which repo, articles and videos belong to each
  data/feeds.json  written by --fetch: Medium posts, YouTube videos (views rounded down), GitHub stars

  python3 scripts/build_content.py           render from the committed data, no network
  python3 scripts/build_content.py --fetch   refresh feeds.json and missing thumbnails, then render
  python3 scripts/build_content.py --check   exit 1 if index.html differs from what the data renders

Each source fails on its own: a feed that errors or comes back empty keeps its previous entry in
feeds.json, so a Medium or YouTube outage never blanks the page. Standard library only.
"""
import argparse
import email.utils
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
SITE = os.path.join(ROOT, "data", "site.json")
FEEDS = os.path.join(ROOT, "data", "feeds.json")
THUMBS = os.path.join(ROOT, "assets", "yt")
LOGOS = os.path.join(ROOT, "assets", "logos")
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
esc = html.escape  # attribute values


def text(s):
    return html.escape(s, quote=False)


def log(msg):
    print(msg, file=sys.stderr)


def get(url, headers=None, timeout=20):
    # Medium turns away unknown clients from datacenter IPs; this is what the old feed action sent.
    req = urllib.request.Request(url, headers={"User-Agent": "rss-parser", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def utc_iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def month(iso):
    d = datetime.fromisoformat(iso)
    return f"{MONTHS[d.month - 1]} {d.year}"


def clean_title(t):
    t = t.replace("\xa0", " ").replace("\u200a", " ")
    t = re.sub(r"\s*\u2014\s*", ": ", t)
    t = re.sub(r",(?=[A-Za-z])", ", ", t)
    return re.sub(r"\s+", " ", t).strip()


def post_id(url):
    path = url.split("?")[0].rstrip("/")
    m = re.search(r"-([0-9a-f]{10,})$", path)
    return m.group(1) if m else path.rsplit("/", 1)[-1]


# Fetchers: each returns fresh data or raises.

def fetch_medium(cfg):
    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    items = []
    for it in ET.fromstring(get(cfg["feed"])).iter("item"):
        url = (it.findtext("link") or "").split("?")[0]
        if not url.startswith("https://"):
            continue
        title = clean_title(it.findtext("title") or "")
        if title.endswith("\u2026"):
            # Medium cuts long titles in the feed; the article body opens with the full one.
            head = title[:-1].rstrip().lower()
            body = it.findtext("content:encoded", "", ns)
            for h in re.findall(r"<h[1-4][^>]*>(.*?)</h[1-4]>", body, re.S):
                full = clean_title(html.unescape(re.sub(r"<[^>]+>", "", h)))
                if full.lower().startswith(head):
                    title = full
                    break
        date = email.utils.parsedate_to_datetime(it.findtext("pubDate"))
        items.append({"id": post_id(url), "title": title, "url": url, "date": utc_iso(date)})
    if not items:
        raise ValueError("no posts in the feed")
    return items


def round_views(n):
    if n >= 1000:
        return n // 1000 * 1000
    if n >= 100:
        return n // 100 * 100
    return n // 10 * 10


def fetch_youtube(cfg):
    a, yt, m = "{http://www.w3.org/2005/Atom}", "{http://www.youtube.com/xml/schemas/2015}", "{http://search.yahoo.com/mrss/}"
    items = []
    for en in ET.fromstring(get(cfg["feed"])).findall(a + "entry"):
        vid = en.findtext(yt + "videoId") or ""
        if not VIDEO_ID.match(vid):
            continue
        stats = en.find(f"{m}group/{m}community/{m}statistics")
        views = int(stats.get("views", "0")) if stats is not None else 0
        published = datetime.fromisoformat(en.findtext(a + "published"))
        items.append({"id": vid, "title": clean_title(en.findtext(a + "title") or ""),
                      "date": utc_iso(published), "views": round_views(views)})
    if not items:
        raise ValueError("no videos in the feed")
    return items


def fetch_stars(user, repos):
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    stars = {}
    for repo in repos:
        data = json.loads(get(f"https://api.github.com/repos/{user}/{repo}", headers))
        stars[repo] = int(data["stargazers_count"])
    return stars


def thumb_file(vid):
    for ext in ("webp", "jpg"):
        if os.path.exists(os.path.join(THUMBS, f"{vid}.{ext}")):
            return f"{vid}.{ext}"
    return None


def fetch_thumb(vid):
    # Largest first. maxresdefault is native 16:9; the others are letterboxed 4:3, which the
    # 16:9 frame crops with object-fit. YouTube answers a missing size with a tiny placeholder.
    for path, ext in ((f"vi_webp/{vid}/maxresdefault.webp", "webp"), (f"vi_webp/{vid}/sddefault.webp", "webp"),
                      (f"vi/{vid}/hqdefault.jpg", "jpg")):
        try:
            data = get("https://i.ytimg.com/" + path)
        except Exception:
            continue
        if len(data) > 4000 and (data[:4] == b"RIFF" or data[:3] == b"\xff\xd8\xff"):
            os.makedirs(THUMBS, exist_ok=True)
            with open(os.path.join(THUMBS, f"{vid}.{ext}"), "wb") as f:
                f.write(data)
            return
    log(f"thumbnail: none found for {vid}")


def refresh(site, feeds):
    sources = {
        "articles": lambda: fetch_medium(site["medium"]),
        "videos": lambda: fetch_youtube(site["youtube"]),
        "stars": lambda: fetch_stars(site["github_user"], [p["repo"] for p in site["projects"]]),
    }
    for key, fn in sources.items():
        try:
            feeds[key] = fn()
            log(f"{key}: ok")
        except Exception as ex:
            log(f"{key}: kept the previous data ({type(ex).__name__}: {ex})")
    for v in feeds.get("videos", []):
        if not thumb_file(v["id"]):
            fetch_thumb(v["id"])
    return feeds


# Rendering: plain string building, deterministic for the same data.

def views_label(n):
    if n >= 1000:
        return f"{n // 1000}K+ views"
    if n >= 10:
        return f"{n}+ views"
    return ""


def tags(p):
    items = []
    for slug, name in p["tags"]:
        if not any(os.path.exists(os.path.join(LOGOS, f"{slug}.{x}")) for x in ("svg", "png")):
            sys.exit(f"{p['id']}: no logo file for tag '{slug}'")
        items.append(f'<li><span class="ic i-{esc(slug)}" aria-hidden="true"></span>{text(name)}</li>')
    return '<ul class="tags">' + "".join(items) + "</ul>"


def links(p, articles, site, video=None):
    out = [f'<a href="https://github.com/{esc(site["github_user"])}/{esc(p["repo"])}">Code</a>']
    if video:
        out.append(f'<a href="https://www.youtube.com/watch?v={video["id"]}">YouTube</a>')
    for aid in p["articles"]:
        if aid in articles:
            label = site["medium"]["labels"].get(aid, "Article")
            out.append(f'<a href="{esc(articles[aid]["url"])}">{text(label)}</a>')
    return '<p class="links">' + "".join(out) + "</p>"


def kind_line(p, stars):
    n = stars.get(p["repo"])
    count = f' · <span class="stars">{n}</span> {"star" if n == 1 else "stars"}' if n else ""
    return f'<p class="kind-line">{text(p["kind"])}{count}</p>'


def player(v):
    title = esc(v["title"])
    badge = " · ".join(x for x in (views_label(v["views"]), month(v["date"])) if x)
    return "\n".join([
        '<div class="player">',
        f'  <a class="yt" href="https://www.youtube.com/watch?v={v["id"]}" data-yt="{v["id"]}" data-title="{title}">',
        f'    <img src="assets/yt/{thumb_file(v["id"])}" width="1280" height="720" loading="lazy" decoding="async" alt="">',
        '    <span class="play" aria-hidden="true"></span>',
        f'    <span class="badge" aria-hidden="true">{text(badge)}</span>',
        f'    <span class="vh">Play video: {text(v["title"])}</span>',
        "  </a>",
        "</div>",
    ])


def indent(block, n):
    pad = " " * n
    return "\n".join(pad + line if line else line for line in block.split("\n"))


def render_projects(site, feeds):
    videos = {v["id"]: v for v in feeds.get("videos", []) if thumb_file(v["id"])}
    articles = {a["id"]: a for a in feeds.get("articles", [])}
    stars = feeds.get("stars", {})
    showcase, rest, used = [], [], set()
    for p in site["projects"]:
        repo_url = f'https://github.com/{esc(site["github_user"])}/{esc(p["repo"])}'
        video = next((videos[v] for v in p["videos"] if v in videos), None)
        body = "\n".join([
            kind_line(p, stars),
            f'<h3><a href="{repo_url}">{text(p["title"])}</a></h3>',
            f'<p>{text(p["blurb"])}</p>',
            tags(p),
            links(p, articles, site, video),
        ])
        if video:
            used.add(video["id"])
            showcase.append(f'<article class="card video-card" id="p-{esc(p["id"])}">\n{indent(player(video), 2)}\n'
                            f'  <div class="card-body">\n{indent(body, 4)}\n  </div>\n</article>')
        else:
            rest.append(f'<article class="card" id="p-{esc(p["id"])}">\n{indent(body, 2)}\n</article>')
    # Videos that don't belong to a project yet still get a playable card, newest first.
    extra = sorted((v for v in videos.values() if v["id"] not in used), key=lambda v: v["date"], reverse=True)
    for v in extra[: max(0, site["youtube"]["max"] - len(used))]:
        body = "\n".join([
            '<p class="kind-line">video</p>',
            f'<h3><a href="https://www.youtube.com/watch?v={v["id"]}">{text(v["title"])}</a></h3>',
        ])
        showcase.append(f'<article class="card video-card" id="v-{v["id"]}">\n{indent(player(v), 2)}\n'
                        f'  <div class="card-body">\n{indent(body, 4)}\n  </div>\n</article>')
    parts = []
    if showcase:
        parts.append('<div class="showcase">\n' + indent("\n".join(showcase), 2) + "\n</div>")
    if rest:
        parts.append('<div class="projects">\n' + indent("\n".join(rest), 2) + "\n</div>")
    return "\n".join(parts)


def render_articles(site, feeds):
    cfg = site["medium"]
    owner = {aid: p for p in site["projects"] for aid in p["articles"]}

    def sort_key(a):
        shift = cfg["sort_shift_hours"].get(a["id"], 0)
        return datetime.fromisoformat(a["date"]) + timedelta(hours=shift)

    posts = [a for a in feeds.get("articles", []) if a["id"] not in cfg["skip"]]
    posts.sort(key=sort_key, reverse=True)
    rows = []
    for a in posts[: cfg["max"]]:
        title = cfg["titles"].get(a["id"], a["title"])
        proj = owner.get(a["id"])
        tag = f'<a class="proj" href="#p-{esc(proj["id"])}">{text(proj["repo"])}</a>' if proj else ""
        rows.append(f'  <li><span class="date">{month(a["date"])}</span><a href="{esc(a["url"])}">{text(title)}</a>{tag}</li>')
    return '<ul class="feed">\n' + "\n".join(rows) + "\n</ul>"


def replace_block(page, name, block):
    start, end = f"<!-- {name}:START -->", f"<!-- {name}:END -->"
    m = re.search(re.escape(start) + r".*?\n([ \t]*)" + re.escape(end), page, re.S)
    if not m or page.count(start) != 1:
        sys.exit(f"index.html: expected exactly one {start} ... {end} pair")
    pad = len(m.group(1))
    return page[: m.start()] + start + "\n" + indent(block, pad) + "\n" + m.group(1) + end + page[m.end():]


def render(page, site, feeds):
    page = replace_block(page, "PROJECTS", render_projects(site, feeds))
    return replace_block(page, "ARTICLES", render_articles(site, feeds))


def dump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fetch", action="store_true", help="refresh feeds.json and thumbnails first")
    ap.add_argument("--check", action="store_true", help="fail if index.html is out of date")
    args = ap.parse_args()

    with open(SITE, encoding="utf-8") as f:
        site = json.load(f)
    ids = [p["id"] for p in site["projects"]]
    if len(ids) != len(set(ids)):
        sys.exit("site.json: project ids must be unique")
    feeds = {}
    if os.path.exists(FEEDS):
        with open(FEEDS, encoding="utf-8") as f:
            feeds = json.load(f)

    if args.fetch:
        before = dump(feeds)
        feeds = refresh(site, feeds)
        if dump(feeds) != before:
            with open(FEEDS, "w", encoding="utf-8") as f:
                f.write(dump(feeds))

    with open(INDEX, encoding="utf-8") as f:
        page = f.read()
    out = render(page, site, feeds)
    if args.check:
        if out != page:
            sys.exit("index.html is out of date: run python3 scripts/build_content.py and commit the result")
        log("index.html matches data/")
        return
    if out != page:
        with open(INDEX, "w", encoding="utf-8") as f:
            f.write(out)
        log("index.html updated")
    else:
        log("index.html unchanged")


if __name__ == "__main__":
    main()
