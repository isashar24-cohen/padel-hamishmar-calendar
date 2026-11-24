# Sync tools

Run by the scheduled "Mishmar league sync" task, twice a day:

1. `hapoel_sync.py OUT_DIR` reads the three padel houses from the Hapoel Tel Aviv workplace league site and writes `h1.json`, `h2.json`, `h3.json`, `meta.json`.
2. `med_sync.py DB_DIR OUT_JSON` computes each linked player's own record (medical date and the team's results) from an export of the league page's database.
3. `make_ics.py OUT_DIR REPO_DIR` regenerates the subscription calendars in this repository and prints which files changed.

Only the `.ics` files and these tools live here; no personal data is ever written to this public repository.
