"""从大都会博物馆 Open Access 接口取公有领域中国绘画，用作样片画面。
只取 isPublicDomain=True 的作品，下载 primaryImage（高清 JPEG）。
"""
import json
import os
import subprocess
import sys

UA = "WorkBuddy-EduVideo/1.0 (public domain artwork fetch)"
SEARCH = "https://collectionapi.metmuseum.org/public/collection/v1.1/search"
OBJECT = "https://collectionapi.metmuseum.org/public/collection/v1/objects/%s"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")

QUERIES = {
    "wintry":  "Chinese winter landscape snow",
    "sushi":   "Su Shi",
    "fish":    "Chinese painting fish",
    "plow":    "Chinese painting plowing cultivation",
    "hermit":  "Chinese landscape scholar pavilion",
}


def get(url, binary=False):
    r = subprocess.run(["curl", "-sSL", "-m", "60", "-A", UA, url], capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def search(kw, limit=8):
    url = "%s?q=%s&departmentId=6&hasImages=true&limit=%d" % (
        SEARCH, kw.replace(" ", "+"), limit)
    try:
        return json.loads(get(url)).get("objectIDs") or []
    except Exception:
        return []


def detail(oid):
    try:
        return json.loads(get(OBJECT % oid))
    except Exception:
        return None


def public_domain(d):
    return d and d.get("isPublicDomain") and d.get("primaryImage")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "q":
        ids = search(sys.argv[2], limit=25)
        shown = 0
        for oid in ids:
            d = detail(oid)
            if not public_domain(d):
                continue
            print("  %s  | %s" % (oid, (d.get("title") or "")[:60]))
            print("      %s / %s / %s" % (
                d.get("artistDisplayName") or "-",
                d.get("objectDate") or "-",
                (d.get("medium") or "")[:44]))
            shown += 1
            if shown >= 8:
                break
    elif len(sys.argv) > 1 and sys.argv[1] == "dl":
        oid, name = sys.argv[2], sys.argv[3]
        d = detail(oid)
        if not public_domain(d):
            print("NOT public domain or no image: %s" % oid)
            sys.exit(1)
        os.makedirs(OUT, exist_ok=True)
        data = get(d["primaryImage"], binary=True)
        path = os.path.join(OUT, name + ".jpg")
        open(path, "wb").write(data)
        print("saved %s (%d KB) <- %s | %s" % (
            path, len(data) // 1024, d.get("title"), d.get("objectDate")))
    else:
        for key, kw in QUERIES.items():
            print("=" * 72)
            print("[%s] %s" % (key, kw))
            ids = search(kw)
            shown = 0
            for oid in ids:
                d = detail(oid)
                if not public_domain(d):
                    continue
                print("  %s  | %s" % (oid, (d.get("title") or "")[:60]))
                print("      %s / %s / %s" % (
                    d.get("artistDisplayName") or "-",
                    d.get("objectDate") or "-",
                    (d.get("medium") or "")[:44]))
                shown += 1
                if shown >= 5:
                    break
