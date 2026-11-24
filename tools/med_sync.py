# Mirrors each linked roster entry to med/<player code> (medical date + the team's results), as the page does for admins.
# Usage: python3 -I med_sync.py DB_DIR OUT_JSON   (DB_DIR holds official/, coord/, res/ and med/ exported as <doc_id>.json)
import json, os, re, sys
UID = re.compile(r"^u_[A-Za-z0-9_-]{10,40}$"); DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$"); PID = re.compile(r"^p[a-z0-9]{4,12}$")
GID = re.compile(r"^h[1-3]-[\w-]{1,24}$"); DMY = re.compile(r"^\d\d\.\d\d\.\d{4}$")
LABEL = ["משחק 1", "משחק 2", "משחק 3"]
def docs(d):
    p = os.path.join(sys.argv[1], d)
    return {f[:-5]: json.load(open(os.path.join(p, f), encoding="utf-8")) for f in os.listdir(p) if f.endswith(".json")} if os.path.isdir(p) else {}
isint = lambda v: isinstance(v, int) and not isinstance(v, bool)
def set_ok(x): return isinstance(x, dict) and isint(x.get("h")) and isint(x.get("a")) and 0 <= x["h"] <= 7 and 0 <= x["a"] <= 7 and x["h"] != x["a"] and max(x["h"], x["a"]) >= 6
def tb_ok(x):
    if not (isinstance(x, dict) and isint(x.get("h")) and isint(x.get("a")) and 0 <= x["h"] <= 40 and 0 <= x["a"] <= 40): return False
    hi, d = max(x["h"], x["a"]), abs(x["h"] - x["a"]); return hi >= 10 and d >= 2 and (hi == 10 or d == 2)
def parse_match(m, i):
    if not isinstance(m, dict): return {"s": [], "tb": None, "p": {"H": [], "A": []}}
    s = [{"h": x.get("h"), "a": x.get("a")} for x in (m.get("s") or [])[:2] if isinstance(x, dict)] if i < 2 and isinstance(m.get("s"), list) else []
    s = [x for x in s if set_ok(x)]; tb = {"h": m["tb"]["h"], "a": m["tb"]["a"]} if tb_ok(m.get("tb")) else None
    pp = lambda v: [x for x in v if isinstance(x, str) and PID.match(x)][:2] if isinstance(v, list) else []
    p = m.get("p") if isinstance(m.get("p"), dict) else {}
    return {"s": s, "tb": tb, "p": {"H": pp(p.get("H")), "A": pp(p.get("A"))}}
def winner(m, i):
    if i == 2: return ("H" if m["tb"]["h"] > m["tb"]["a"] else "A") if m["tb"] else None
    if len(m["s"]) != 2: return None
    h = sum(1 for x in m["s"] if x["h"] > x["a"])
    if h == 2: return "H"
    if h == 0: return "A"
    return ("H" if m["tb"]["h"] > m["tb"]["a"] else "A") if m["tb"] else None
def team_score(r):
    if r["tech"]: return (0 if r["tech"] == "H" else 3, 0 if r["tech"] == "A" else 3)
    h = a = 0
    for i, m in enumerate(r["m"]):
        w = winner(m, i); h += w == "H"; a += w == "A"
    return (h, a)
def tidy(t): return re.sub(r"\s+", " ", re.sub(r"\s*-\s*(?=\S)", " - ", t or "")).strip()
official, coordd, res, med = docs("official"), docs("coord"), docs("res"), docs("med")
coord = {k: v.get("uid") for k, v in coordd.items() if re.fullmatch(r"m[1-6]", k) and isinstance(v.get("uid"), str)}
ours = lambda t: isinstance(t, str) and t.startswith("משמר")
KEY = lambda t: "m" + t[-1]
games, off = [], {}
for h in (1, 2, 3):
    for g in (official.get("h%d" % h) or {}).get("games") or []:
        if not isinstance(g, dict) or not isinstance(g.get("id"), str) or not GID.match(g["id"]): continue
        home, away = g.get("home"), g.get("away")
        home = home[:80] if isinstance(home, str) else None; away = away[:80] if isinstance(away, str) else None
        if not home or (not ours(home) and not ours(away)): continue
        if away and not DMY.match(g.get("date") or ""): continue
        games.append({"id": g["id"], "home": home, "away": away or None, "date": g.get("date")})
        sc = g.get("score")
        if away and isinstance(sc, list) and len(sc) == 2 and all(isint(n) and 0 <= n <= 3 for n in sc): off[g["id"]] = (sc[0], sc[1], g.get("tech") is True)
def roster(k):
    out = []
    for x in ((res.get(coord.get(k)) or {}).get("rosters") or {}).get(k) or []:
        if not isinstance(x, dict) or not isinstance(x.get("id"), str) or not PID.match(x["id"]): continue
        first, last = str(x.get("first") or "").strip()[:30], str(x.get("last") or "").strip()[:30]
        if not first and not last:
            parts = str(x.get("name") or "").strip()[:40].split(" "); first, last = parts[0], " ".join(parts[1:])
        out.append({**x, "first": first, "last": last, "name": (first + " " + last).strip() or "שחקן"})
    return out
def pname(t, pid):
    for x in roster(KEY(t)):
        if x["id"] == pid: return x["name"]
    return "שחקן שהוסר"
def sheet_game(u, gid):
    r = ((res.get(u) or {}).get("games") or {}).get(gid)
    if not isinstance(r, dict): return None
    tech = r.get("tech") if r.get("tech") in ("H", "A") else None
    m = [] if tech else [parse_match((r.get("m") or [None] * 3)[j] if isinstance(r.get("m"), list) and j < len(r["m"]) else None, j) for j in range(3)]
    return {"tech": tech, "m": m, "at": r.get("at") if isinstance(r.get("at"), str) else ""}
results = {}
for g in games:
    if not g["away"]: continue
    us = list(dict.fromkeys(coord.get(KEY(t)) for t in (g["home"], g["away"]) if ours(t) and coord.get(KEY(t))))
    cands = [c for c in (sheet_game(u, g["id"]) for u in us) if c]
    r = None
    if cands:
        cands.sort(key=lambda c: c["at"], reverse=True); r = dict(cands[0]); r["home"], r["away"] = team_score(r); r["official"] = False; r["offTech"] = False
    if g["id"] in off:
        o = off[g["id"]]; base = dict(r) if r else {"m": [], "tech": None}
        base.update({"home": o[0], "away": o[1], "official": True, "offTech": o[2]}); r = base
    if r: results[g["id"]] = r
def team_results(t):
    out = []
    for g in games:
        if not g["away"] or (g["home"] != t and g["away"] != t) or g["id"] not in results: continue
        r = results[g["id"]]; side = "H" if g["home"] == t else "A"; ms = []
        if not r["tech"]:
            for i, m in enumerate(r["m"]):
                w = winner(m, i)
                if not w: continue
                f = lambda x: "%d-%d" % ((x["h"], x["a"]) if side == "H" else (x["a"], x["h"]))
                ms.append({"n": i, "who": " ו".join(pname(t, pid) for pid in m["p"][side]), "sets": " ".join(f(x) for x in m["s"]), "tb": f(m["tb"]) if m["tb"] else "", "won": w == side})
        out.append({"id": g["id"], "date": g["date"], "opp": tidy(g["away"] if side == "H" else g["home"]), "us": r["home"] if side == "H" else r["away"],
                    "them": r["away"] if side == "H" else r["home"], "off": bool(r["official"]), "tech": bool(r["tech"] or r["offTech"]), "m": ms})
    return out
want = {}
for k in coord:
    t = "משמר " + k[1:]; tr = team_results(t)
    for x in roster(k):
        if x.get("active") is False or not UID.match(str(x.get("uid") or "")): continue
        want[x["uid"]] = {"first": x["first"], "last": x["last"], "team": k, "med": x.get("med") if DATE.match(str(x.get("med") or "")) else "", "games": tr}
sets = {u: v for u, v in want.items() if any((med.get(u) or {}).get(f) != v[f] for f in ("first", "last", "team", "med")) or (med.get(u) or {}).get("games", []) != v["games"]}
dels = [u for u in med if u not in want]
json.dump({"set": sets, "delete": dels}, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
print("med sync:", len(sets), "to set,", len(dels), "to delete")
