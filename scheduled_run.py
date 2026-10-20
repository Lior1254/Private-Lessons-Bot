# ===================================================
# scheduled_run.py
# מורץ ע"י מתזמן המשימות של Windows (setup_schedule.bat).
# 1. Windows מעיר את המחשב משינה בשעה שנקבעה
# 2. הבוט מעלה את הפוסטים (אם היום זו השעה של היום)
# 3. אם המחשב היה ריק כשהתחלנו ועדיין אף אחד לא נוגע בו – מחזיר אותו לשינה
# ===================================================
import os, sys, time, ctypes, logging
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ["BOT_SCHEDULED"] = "1"

from main_keyboard import load_config, run_post_safe, is_todays_slot

log = logging.getLogger("scheduled")
fh = logging.FileHandler("logs/scheduled.log", encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
log.addHandler(fh); log.setLevel(logging.INFO); log.propagate = False

IDLE_AT_START_SEC = 120   # אם אף אחד לא נגע במחשב 2 דק' – כנראה Windows העיר אותו בשבילנו
IDLE_AT_END_SEC = 300     # מחזירים לשינה רק אם אף אחד לא נגע במחשב ב-5 הדקות האחרונות

def idle_seconds():
    """כמה שניות עברו מאז שמישהו נגע בעכבר/מקלדת."""
    if sys.platform != "win32": return 0
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    lii = LASTINPUTINFO(); lii.cbSize = ctypes.sizeof(lii)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    return (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) / 1000

def go_to_sleep():
    # Sleep רגיל (לא Hibernate): hibernate=False, force=False, wakeup events מותרים
    ctypes.windll.powrprof.SetSuspendState(False, False, False)

def current_slot_index(times):
    """לאיזו שעה ברשימה הכי קרובה השעה עכשיו."""
    now = datetime.now()
    mins = now.hour * 60 + now.minute
    diffs = [abs(mins - (int(t.split(":")[0]) * 60 + int(t.split(":")[1]))) for t in times]
    return diffs.index(min(diffs))

def main():
    config = load_config()
    times = config.get("schedule", {}).get("times", ["16:30", "20:30"])
    woke_for_us = idle_seconds() > IDLE_AT_START_SEC
    slot = current_slot_index(times)
    log.info(f"התחלה | שעה {times[slot]} | מחשב היה ריק: {woke_for_us}")

    if is_todays_slot(slot, len(times)):
        try:
            run_post_safe()
            log.info("סיום פרסום")
        except Exception as e:
            log.info(f"שגיאה: {e}")
    else:
        log.info("היום מפרסמים בשעה אחרת – לא מפרסם")

    if woke_for_us and sys.platform == "win32":
        idle = idle_seconds()
        if idle > IDLE_AT_END_SEC:
            log.info("מחזיר את המחשב לשינה")
            time.sleep(5)
            go_to_sleep()
        else:
            log.info(f"מישהו משתמש במחשב (לפני {idle:.0f} שניות) – לא מכבה")

if __name__ == "__main__":
    main()
