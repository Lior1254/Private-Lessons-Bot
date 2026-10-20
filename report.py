# ===================================================
# report.py
# בדיקה אמיתית שהפוסט עלה, תיעוד היסטוריה, ודיווח ל-Discord.
# ===================================================
import os, re, csv, json, time, logging, urllib.request
from datetime import datetime

RESULTS_CSV = "logs/results.csv"
ICONS = {"published": "✅", "pending": "⏳", "unverified": "⚠️", "failed": "❌"}
NAMES = {"published": "Published", "pending": "Pending approval", "unverified": "Unverified", "failed": "Failed"}

# ---------- בדיקה שהפוסט באמת עלה ----------
def snippet_of(message, length=22):
    """קטע קצר מהשורה הראשונה של הפוסט, בלי אימוג'ים – כדי לחפש אותו בדף."""
    first = next((l for l in message.split("\n") if l.strip()), "")
    first = "".join(ch for ch in first if ord(ch) < 0x2000 or 0x2010 <= ord(ch) <= 0x206F or 0xFB1D <= ord(ch) <= 0xFB4F)
    first = re.sub(r"\s+", " ", first).strip()
    return first[:length].strip()

def _count_on(driver, url, snippet):
    driver.get(url)
    time.sleep(4)
    try:
        driver.execute_script("window.scrollBy(0, 1500)"); time.sleep(1.5)
        text = driver.execute_script("return document.body.innerText || ''")
    except Exception:
        return -1
    text = re.sub(r"\s+", " ", text)
    return text.count(snippet)

def content_counts(driver, group_id, snippet):
    """כמה פעמים הקטע מופיע: בפוסטים שלי שפורסמו, בממתינים לאישור, ובפיד הקבוצה."""
    base = f"https://www.facebook.com/groups/{group_id}"
    return {
        "posted": _count_on(driver, f"{base}/my_posted_content", snippet),
        "pending": _count_on(driver, f"{base}/my_pending_content", snippet),
        "feed": _count_on(driver, base, snippet),
    }

def decide_status(before, after):
    """משווים לפני/אחרי הפרסום. רק עלייה במספר = הוכחה שהפוסט החדש שם."""
    def grew(k):  # -1 = הדף לא נטען, לא מסיקים ממנו כלום
        return before[k] >= 0 and after[k] >= 0 and after[k] > before[k]
    if grew("pending"):
        return "pending"
    if grew("posted") or grew("feed"):
        return "published"
    return "unverified"

# ---------- תיעוד ----------
FIELDS = ["time", "run", "mode", "group_id", "group_name", "text_file", "status", "reason", "attempts"]

def save_results(results, run_id, mode):
    new = not os.path.exists(RESULTS_CSV)
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        for r in results:
            w.writerow({"time": datetime.now().strftime("%Y-%m-%d %H:%M"), "run": run_id, "mode": mode,
                        "group_id": r["id"], "group_name": r["name"], "text_file": r["text"],
                        "status": r["status"], "reason": r.get("reason", ""), "attempts": r.get("attempts", 1)})

def history_notes(results, mode):
    """הערות על קבוצות שחוזרות על אותה בעיה (3 ריצות אמיתיות ברצוף)."""
    if mode != "real" or not os.path.exists(RESULTS_CSV): return []
    with open(RESULTS_CSV, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["mode"] == "real"]
    notes = []
    for r in results:
        last = [x["status"] for x in rows if x["group_id"] == r["id"]][-3:]
        if len(last) == 3 and all(s == "failed" for s in last):
            notes.append(f"❌ **{r['name']}** failed 3 runs in a row – check if you can still post there")
        elif len(last) == 3 and all(s == "pending" for s in last):
            notes.append(f"⏳ **{r['name']}** pending approval 3 runs in a row – the admin may not be approving posts")
        elif len(last) == 3 and all(s == "unverified" for s in last):
            notes.append(f"⚠️ **{r['name']}** unverified 3 runs in a row – open the group and check by eye")
    return notes

# ---------- Discord ----------
def send_discord(text):
    url = os.environ.get("DISCORD_WEBHOOK", "").strip()
    if not url:
        logging.info("אין DISCORD_WEBHOOK ב-.env – לא נשלח דיווח"); return False
    if len(text) > 1990: text = text[:1980] + "\n…"
    body = json.dumps({"content": text, "username": "Lessons Bot"}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json",
                                                          "User-Agent": "LessonsBot/1.0"})
    for attempt in range(3):
        try:
            urllib.request.urlopen(req, timeout=20); return True
        except Exception as e:
            logging.info(f"שליחה ל-Discord נכשלה ({e})"); time.sleep(10)
    return False

def run_stats(mode):
    """מספר הריצה (אמיתיות ובדיקות נספרות בנפרד) + כמה ריצות אמיתיות ב-7 הימים האחרונים."""
    if not os.path.exists(RESULTS_CSV): return 1, 0
    with open(RESULTS_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    runs = {}
    for r in rows:
        runs.setdefault((r["mode"], r["run"]), r["time"])
    number = sum(1 for (m, _) in runs if m == mode)
    week_ago = datetime.now().timestamp() - 7 * 86400
    last_week = sum(1 for (m, _), t in runs.items()
                    if m == "real" and datetime.strptime(t, "%Y-%m-%d %H:%M").timestamp() >= week_ago)
    return number, last_week

def build_report(results, started, mode, extra_notes=()):
    counts = {k: sum(1 for r in results if r["status"] == k) for k in ICONS}
    ok = counts["published"] + counts["pending"]
    minutes = (datetime.now() - started).total_seconds() / 60
    number, last_week = run_stats(mode)
    if mode == "demo":
        title = f"🧪 **Test run #{number}** · {started:%a %d/%m/%Y · %H:%M} · demo groups"
    else:
        title = f"🤖 **Run #{number}** · {started:%a %d/%m/%Y · %H:%M}"
    lines = [title,
             f"**{ok}/{len(results)} posted**  ·  ⏱ {minutes:.0f} min  ·  📅 {last_week} real runs in the last 7 days",
             ""]
    lines += [f"{ICONS[k]} {NAMES[k]}: **{counts[k]}**" for k in ICONS]
    lines += ["", "**Groups**"]
    order = {"failed": 0, "unverified": 1, "pending": 2, "published": 3}
    for r in sorted(results, key=lambda r: order[r["status"]]):
        line = f"{ICONS[r['status']]} {r['name']}"
        if r["status"] == "failed" and r.get("reason"): line += f" — {r['reason']}"
        if r.get("attempts", 1) > 1: line += " (2nd try)"
        lines.append(line)
    notes = list(extra_notes) + history_notes(results, mode)
    if notes:
        lines += ["", "**Notes**"] + notes
    return "\n".join(lines)
