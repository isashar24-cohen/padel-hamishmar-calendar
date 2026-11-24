# Reads the three padel houses of the Hapoel Tel Aviv workplace league (season 2026/27)
# and writes one JSON file per house plus meta.json into the output directory.
# Usage: python3 -I hapoel_sync.py OUT_DIR   (exit code 0 only when all three houses parsed)
import re, html, json, sys, hashlib, urllib.request, datetime, os
BASE = "https://www.hapoel-telaviv-ma.co.il/?m=leagues&season=31&branch=26&league="
HOUSES = {1: 1138, 2: 1135, 3: 1151}
MISHMAR = {"משמר %d" % i for i in range(1, 7)}
def txt(x): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip()
def gid(h, r, a, b): return "h%d-%s" % (h, hashlib.sha1(("%d|%s|%s" % (r, a, b)).encode()).hexdigest()[:10])
def parse(h, s):
    if "פאדל" not in s or "לוח משחקים" not in s: raise ValueError("page shape changed (house %d)" % h)
    tbl, sched = s[s.find("טבלת הליגה"):s.find("לוח משחקים")], s[s.find("לוח משחקים"):]
    table = []
    for tr in re.findall(r"<tr>(.*?)</tr>", tbl, flags=re.S):
        tds = [txt(re.sub(r"<font.*?</font>", "", x, flags=re.S)) for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        if len(tds) == 6 and tds[0].isdigit():
            n = lambda v: int(v) if v.isdigit() else 0
            table.append({"pos": n(tds[0]), "team": tds[1], "played": n(tds[2]), "w": n(tds[3]), "l": n(tds[4]), "pts": n(tds[5])})
    games, rnd = [], None
    for tr in re.findall(r"<tr>(.*?)</tr>", sched, flags=re.S):
        m = re.search(r"מספר מחזור</u>:\s*(\d+)", tr)
        if m: rnd = int(m.group(1)); continue
        tds = [txt(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        if len(tds) != 7 or rnd is None or tds[0] == "שם קבוצה": continue
        a, b, d, _day, t, court, res = tds
        sm = re.match(r"(\d+)\s*-\s*(\d+)", res)
        if d and not re.fullmatch(r"\d\d\.\d\d\.\d{4}", d): raise ValueError("date format changed: %r" % d)
        games.append({"id": gid(h, rnd, a, b) if b else "h%d-bye-%d" % (h, rnd), "house": h, "round": rnd, "home": a, "away": b or None,
                      "date": d or None, "time": t or None, "court": court or None,
                      "score": [int(sm.group(1)), int(sm.group(2))] if sm else None, "tech": "(ט)" in res})
    if len(games) < 10: raise ValueError("too few games in house %d: %d" % (h, len(games)))
    if not any(g["home"] in MISHMAR or g["away"] in MISHMAR for g in games): raise ValueError("no Mishmar team in house %d" % h)
    return {"house": h, "league": HOUSES[h], "table": table, "games": games}
def main(out):
    os.makedirs(out, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        docs = {}
        for h, lid in HOUSES.items():
            req = urllib.request.Request(BASE + str(lid), headers={"User-Agent": "Mozilla/5.0 (league schedule reader)", "Cookie": "season=31"})
            docs[h] = parse(h, urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
        for h, d in docs.items():
            d["fetchedAt"] = now
            json.dump(d, open(os.path.join(out, "h%d.json" % h), "w", encoding="utf-8"), ensure_ascii=False)
        json.dump({"ok": True, "fetchedAt": now, "attemptAt": now}, open(os.path.join(out, "meta.json"), "w"))
        print("OK", {h: len(d["games"]) for h, d in docs.items()}); return 0
    except Exception as e:
        json.dump({"ok": False, "attemptAt": now, "error": str(e)[:200]}, open(os.path.join(out, "meta.json"), "w"))
        print("FAILED", e); return 1
sys.exit(main(sys.argv[1]))
