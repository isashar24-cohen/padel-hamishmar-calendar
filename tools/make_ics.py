# Builds the public subscription calendars from the synced league data.
# Usage: python3 -I make_ics.py SYNC_OUT_DIR CAL_DIR   (SYNC_OUT_DIR holds h1.json, h2.json, h3.json from hapoel_sync.py)
# Writes mishmar-1.ics ... mishmar-6.ics and mishmar-all.ics; prints which files changed.
import json, os, re, sys, datetime, zoneinfo
IL = zoneinfo.ZoneInfo("Asia/Jerusalem")
ADDR = {"פאדל סנטר ראשלצ": "פאדל סנטר ראשון לציון"}
DEFAULT_ADDR = "קאנטרי חולון, רחוב הלוחמים 30, חולון"
DAYS = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
def tidy(t): return re.sub(r"\s+", " ", re.sub(r"\s*-\s*(?=\S)", " - ", t or "")).strip()
def esc(v): return str(v).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
def fold(line):
    out, cur, n = [], "", 0
    for ch in line:
        k = len(ch.encode("utf-8"))
        if n + k > (74 if out else 75): out.append(cur); cur, n = "", 0
        cur += ch; n += k
    out.append(cur); return "\r\n ".join(out)
games = []
for h in (1, 2, 3):
    d = json.load(open(os.path.join(sys.argv[1], "h%d.json" % h), encoding="utf-8"))
    for g in d["games"]:
        if g.get("away") and g.get("date") and ("משמר" in g["home"] or "משמר" in g["away"]): games.append(g)
def vevent(g, team):
    d, m, y = map(int, g["date"].split(".")); hh, mm = map(int, (g.get("time") or "19:00").split(":"))
    start = datetime.datetime(y, m, d, hh, mm, tzinfo=IL); end = start + datetime.timedelta(hours=2)
    z = lambda t: t.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    title = "פאדל: %s נגד %s" % (tidy(g["home"]), tidy(g["away"]))
    loc = ADDR.get(g.get("court"), DEFAULT_ADDR)
    desc = "ליגת מקומות העבודה של הפועל ת\"א, בית ערב %d, מחזור %d.\nלהגיע עם כרטיס ליגה דיגיטלי בטלפון ובתלבושת מתאימה. איחור של יותר מ־15 דקות הוא הפסד טכני." % (g["house"], g["round"])
    uid = "%s-%s@mishmar-padel" % (g["id"], team)
    # DTSTAMP is fixed per game so an unchanged schedule produces an identical file (no needless commits)
    return ["BEGIN:VEVENT", "UID:" + uid, "DTSTAMP:" + z(start), "DTSTART:" + z(start), "DTEND:" + z(end), "SUMMARY:" + esc(title),
            "LOCATION:" + esc(loc), "DESCRIPTION:" + esc(desc), "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + esc(title), "TRIGGER:-PT3H", "END:VALARM", "END:VEVENT"]
def calendar(name, rows):
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Mishmar padel league//HE", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         "X-WR-CALNAME:" + esc(name), "X-WR-TIMEZONE:Asia/Jerusalem", "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    for r in rows: L += r
    L.append("END:VCALENDAR"); return "\r\n".join(fold(l) for l in L) + "\r\n"
os.makedirs(sys.argv[2], exist_ok=True); changed = []
def write(fn, text):
    p = os.path.join(sys.argv[2], fn); old = open(p, encoding="utf-8", newline="").read() if os.path.exists(p) else None
    if old != text: open(p, "w", encoding="utf-8", newline="").write(text); changed.append(fn)
for i in range(1, 7):
    t = "משמר %d" % i
    write("mishmar-%d.ics" % i, calendar("פאדל " + t, [vevent(g, "m%d" % i) for g in games if t in (g["home"], g["away"])]))
write("mishmar-all.ics", calendar("פאדל המשמר (כל הקבוצות)", [vevent(g, "all") for g in games]))
print("changed:", " ".join(changed) if changed else "none")
