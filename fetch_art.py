"""从 Wikimedia Commons 抓取公有领域的中国古代绘画，用作样片画面素材。
只用 Open Access / 公有领域作品，下载的是缩略图（JPEG）。
"""
import json
import os
import subprocess
import sys
import urllib.parse

UA = "WorkBuddy-EduVideo/1.0 (public domain artwork fetch)"
API = "https://commons.wikimedia.org/w/api.php"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")


def curl(url, binary=False):
    """走 curl —— 本机 Python 的 HTTPS 握手会失败，curl 可以正常出网。"""
    cmd = ["curl", "-sSL", "-m", "90", "-A", UA, url]
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")

QUERIES = {
    "hut_rain": "Chinese painting winter landscape pavilion snow Song",
    "prison":  "Su Shi painting wood rock Northern Song",
    "fish":    "Chinese painting fish album leaf Song Yuan",
    "plow":    "Chinese painting plowing rice cultivation Gengzhi tu",
}


def api(params):
    url = API + "?" + urllib.parse.urlencode(params)
    return json.loads(curl(url))


def search(query, limit=6):
    data = api({
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": 1920,
        "format": "json",
    })
    out = []
    for p in (data.get("query", {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if not ii.get("thumburl"):
            continue
        meta = ii.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "?")
        out.append({
            "title": p["title"],
            "thumb": ii["thumburl"],
            "w": ii.get("width"),
            "h": ii.get("height"),
            "license": lic,
        })
    return out


def download(item, name):
    os.makedirs(OUT, exist_ok=True)
    data = curl(item["thumb"], binary=True)
    path = os.path.join(OUT, name + ".jpg")
    with open(path, "wb") as f:
        f.write(data)
    return path, len(data)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "search"
    if mode == "search":
        for key, q in QUERIES.items():
            print("=" * 70)
            print("[" + key + "]  " + q)
            for i, it in enumerate(search(q)):
                print("  %d) %s" % (i, it["title"][:78]))
                print("     %sx%s  license=%s" % (it["w"], it["h"], it["license"]))
    else:
        # download: fetch_art.py dl <key> <index> <outname>
        key, idx, name = sys.argv[2], int(sys.argv[3]), sys.argv[4]
        items = search(QUERIES[key])
        it = items[idx]
        p, n = download(it, name)
        print("saved %s  (%d KB)  <- %s" % (p, n // 1024, it["title"]))
