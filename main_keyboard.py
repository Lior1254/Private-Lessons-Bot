# ===================================================
# main_keyboard.py
# כותב כותרת דרך המקלדת (pyautogui) – מצריך Chrome בפוקוס
# ===================================================
import os, json, random, logging, time, threading
import keyboard, pyperclip, pyautogui
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta, time as dtime
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from selenium import webdriver
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

load_dotenv()
os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename="logs/history.log", level=logging.INFO,
                    format="%(asctime)s - %(message)s", encoding="utf-8")

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def is_shabbat(config):
    now = datetime.now()
    weekday = now.weekday()
    friday_cutoff = dtime(*map(int, config["shabbat"]["friday_cutoff"].split(":")))
    saturday_end  = dtime(*map(int, config["shabbat"]["saturday_end"].split(":")))
    if weekday == 4 and now.time() >= friday_cutoff: return True
    if weekday == 5 and now.time() < saturday_end:   return True
    return False

def is_posting_hours(config):
    now = datetime.now().time()
    return dtime(config["post_hours"]["start"], 0) <= now <= dtime(config["post_hours"]["end"], 0)

def get_texts_for_groups(n):
    """מחזיר n טקסטים – כל קבוצה מקבלת טקסט אחר (בלי חזרות עד שנגמרים)."""
    files = [f for f in os.listdir("posts/texts") if f.endswith(".txt")]
    picked = []
    while len(picked) < n:
        batch = files[:]
        random.shuffle(batch)
        picked.extend(batch)
    result = []
    for name in picked[:n]:
        with open(os.path.join("posts/texts", name), "r", encoding="utf-8") as f:
            result.append((f.read().strip(), name))
    return result

STATE_FILE = "logs/last_posted.json"

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f: json.dump(state, f, ensure_ascii=False, indent=1)

def get_image_path():
    images = [f for f in os.listdir("posts/images")
              if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    return os.path.abspath(os.path.join("posts/images", random.choice(images)))

COOKIES_FILE = "fb_cookies.json"

def create_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def save_cookies(driver):
    with open(COOKIES_FILE, "w") as f: json.dump(driver.get_cookies(), f)

def load_cookies(driver):
    if not os.path.exists(COOKIES_FILE): return False
    driver.get("https://www.facebook.com")
    time.sleep(1)
    with open(COOKIES_FILE, "r") as f: cookies = json.load(f)
    for c in cookies:
        try: driver.add_cookie(c)
        except: pass
    driver.refresh()
    time.sleep(2)
    return True

def ensure_logged_in(driver):
    if load_cookies(driver) and "login" not in driver.current_url:
        return
    driver.get("https://www.facebook.com")
    print("\n  [!] התחבר ידנית בחלון שנפתח ולחץ Enter")
    input("  Enter: ")
    save_cookies(driver)

# ========== פרסום – כתיבה דרך מקלדת ==========
def post_to_group(driver, group_id, message, image_path, title=""):
    driver.get(f"https://www.facebook.com/groups/{group_id}")
    time.sleep(1.5)

    button_clicked = False
    for xpath in [
        "//span[text()='יצירת פוסט']",
        "//span[text()='כתיבת פוסט']",
        "//span[text()='צור פוסט']",
        "//span[text()='Create post']",
        "//span[text()='Write something']",
        "//div[@role='button'][contains(.,'יצירת פוסט')]",
        "//div[@role='button'][contains(.,'כתיבת פוסט')]",
        "//div[@role='button'][contains(.,'צור פוסט')]",
        "//div[@role='button'][contains(.,'כאן כותבים')]",
        "//div[@role='button'][contains(.,'Write something')]",
    ]:
        try:
            WebDriverWait(driver, 1.5).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
            time.sleep(0.5)
            button_clicked = True
            break
        except TimeoutException: continue

    if not button_clicked:
        # fallback: לחץ ישירות על תיבת הטקסט (פוסט מהיר ללא כפתור)
        for xp in [
            "//*[@aria-placeholder='כאן כותבים...']",
            "//*[@aria-placeholder='Write something...']",
            "//div[@role='dialog']//div[@contenteditable='true']",
            "//div[contains(@aria-placeholder,'כאן')]",
            "//div[contains(@aria-placeholder,'Write')]",
        ]:
            try:
                WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xp))).click()
                time.sleep(1)
                button_clicked = True
                break
            except TimeoutException: continue

    if not button_clicked:
        buttons = driver.find_elements(By.XPATH, "//div[@role='button'] | //span[@role='button']")
        texts = [b.text.strip() for b in buttons if b.text.strip()][:15]
        print(f"    [!] כפתור יצירת פוסט לא נמצא. כפתורים בדף: {texts}")
        return False

    try:
        WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
    except TimeoutException:
        print("    [!] דיאלוג פרסום לא נפתח")
        return False
    time.sleep(1)

    if title:
        title_written = False
        combined_xpath = (
            "//input[@placeholder='הוספת כותרת']"
            " | //input[@placeholder='Add a title']"
            " | //div[@role='dialog']//input[contains(@placeholder,'כותרת')]"
            " | //div[@role='dialog']//input[contains(@placeholder,'itle')]"
            " | //div[@role='dialog']//*[@aria-label='הוספת כותרת']"
            " | //div[@role='dialog']//*[@aria-placeholder='הוספת כותרת']"
            " | //div[@role='dialog']//*[@data-placeholder='הוספת כותרת']"
            " | //div[@role='dialog']//*[@aria-label='Add a title']"
            " | //div[@role='dialog']//*[@aria-placeholder='Add a title']"
            " | //div[@role='dialog']//*[contains(@aria-placeholder,'יצירת פוסט')]"
            " | //div[@role='dialog']//*[contains(@data-placeholder,'יצירת פוסט')]"
            " | //div[@role='dialog']//*[contains(@placeholder,'יצירת פוסט')]"
        )
        try:
            title_field = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, combined_xpath))
            )
            driver.execute_script("arguments[0].focus(); arguments[0].click();", title_field)
            time.sleep(0.2)
            pyperclip.copy(title)
            title_field.send_keys(Keys.CONTROL, 'v')
            time.sleep(0.2)
            title_written = True
        except TimeoutException:
            pass
        if not title_written:
            import pygetwindow as gw
            try:
                wins = [w for w in gw.getAllWindows()
                        if 'chrome' in w.title.lower() or 'facebook' in w.title.lower()]
                if wins:
                    wins[0].activate()
                    time.sleep(0.5)
            except Exception:
                pass
            pyperclip.copy(title)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.1)

    for xp in ["//*[@aria-placeholder='כאן כותבים...']",
               "//*[@aria-placeholder='Write something...']",
               "//div[@role='dialog']//div[@contenteditable='true']"]:
        try:
            box = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, xp)))
            driver.execute_script("arguments[0].focus(); arguments[0].click();", box)
            time.sleep(0.2)
            pyperclip.copy(message)
            box.send_keys(Keys.CONTROL, 'v')
            break
        except TimeoutException: continue

    win_path = os.path.abspath(image_path).replace("/", "\\")
    try:
        inputs = driver.find_elements(By.XPATH, "//div[@role='dialog']//input[@type='file']")
        if not inputs: inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
        for inp in inputs:
            try:
                driver.execute_script("arguments[0].style.display='block';", inp)
                inp.send_keys(win_path)
                time.sleep(0.5)
                break
            except: continue
    except Exception as e:
        print(f"    [!] שגיאת תמונה: {e}")

    time.sleep(0.3)

    for xp in ["//div[@role='dialog']//div[@role='button'][.//span[text()='פרסום']]",
               "//div[@role='dialog']//div[@role='button'][.//span[text()='פרסם']]",
               "//div[@role='dialog']//div[@role='button'][.//span[text()='Post']]",
               "//div[@role='dialog']//div[@aria-label='פרסום']"]:
        try:
            WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xp))).click()
        except TimeoutException: continue
        # מחכים שהפוסט באמת יעלה (התמונה צריכה זמן) – עד שחלון הפרסום נסגר
        try:
            WebDriverWait(driver, 60).until_not(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//div[@role='button'][.//span[text()='פרסום' or text()='פרסם' or text()='Post']]")))
        except TimeoutException:
            print("    [!] חלון הפרסום לא נסגר אחרי 60 שניות", end=" ")
            return False
        time.sleep(random.uniform(10, 15))
        return True

    return False


def run_post():
    config = load_config()
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')

    if config.get("test_mode"):
        mode = "[TEST]"
    else:
        if is_shabbat(config):
            print(f"[{now_str}] שבת שלום!"); return
        if not is_posting_hours(config):
            print(f"[{now_str}] מחוץ לשעות"); return
        mode = ""

    sched = config.get("schedule", {})
    min_gap = sched.get("min_minutes_between_groups", 3)
    max_gap = sched.get("max_minutes_between_groups", 8)
    min_hours = sched.get("min_hours_between_posts_same_group", 20)

    state = load_state()
    groups = []
    for g in config["groups"]:
        last = state.get(g["id"])
        if last and not config.get("test_mode"):
            hours = (datetime.now() - datetime.fromisoformat(last)).total_seconds() / 3600
            if hours < min_hours:
                print(f"  דילוג על '{g['name']}' – פורסם לפני {hours:.0f} שעות")
                continue
        groups.append(g)
    if not groups:
        print(f"[{now_str}] אין קבוצות לפרסם כרגע"); return
    random.shuffle(groups)  # סדר אחר בכל פעם – נראה פחות כמו בוט

    texts = get_texts_for_groups(len(groups))
    image_path = get_image_path()
    title = config.get("post_title", "")
    total = len(groups)
    print(f"\n[{now_str}] {mode} מתחיל – {total} קבוצות, {min_gap}-{max_gap} דקות בין קבוצה לקבוצה")

    driver = create_driver()
    try:
        ensure_logged_in(driver)
        for i, group in enumerate(groups):
            gid, gname = group["id"], group["name"]
            message, text_file = texts[i]
            remaining = total - i - 1
            print(f"  [{i+1}/{total}] {gname}...", end=" ", flush=True)
            try:
                success = post_to_group(driver, gid, message, image_path, title)
            except Exception as e:
                print(f"✗ שגיאה: {e}"); success = False
            if success:
                logging.info(f"הועלה ל'{gname}' | {text_file}")
                state[gid] = datetime.now().isoformat(timespec="seconds")
                save_state(state)
                suffix = f"נשארו {remaining}" if remaining > 0 else "סיום!"
                print(f"✓  ({suffix})")
            else:
                print("✗ נכשל")
            if remaining > 0:
                wait = random.uniform(min_gap, max_gap) * 60
                print(f"    ממתין {wait/60:.1f} דקות...")
                time.sleep(wait)
    except KeyboardInterrupt: raise
    finally:
        try:
            time.sleep(2)
            driver.quit()
        except: pass

def run_post_safe():
    for attempt in range(1, 4):
        try:
            run_post(); return
        except KeyboardInterrupt: raise
        except Exception as e:
            print(f"  [!] ניסיון {attempt}/3 נכשל: {e}")
            if attempt < 3: time.sleep(30 * attempt)
            else: print("  [!] נכשל 3 פעמים – מדלג")

def is_todays_slot(slot_index, slots_count):
    """פוסט אחד ביום – כל יום משתמשים בשעה אחרת מהרשימה (מתחלף)."""
    return datetime.now().date().toordinal() % slots_count == slot_index

if __name__ == "__main__":
    print("=" * 45)
    print("  Facebook Bot – מצב מקלדת")
    print("=" * 45)
    config = load_config()
    times = config.get("schedule", {}).get("times", ["16:30", "20:30"])

    if config.get("test_mode"):
        run_post_safe()

    scheduler = BlockingScheduler(timezone="Asia/Jerusalem")
    for idx, t in enumerate(times):
        h, m = map(int, t.split(":"))
        def job(idx=idx, t=t):
            if is_todays_slot(idx, len(times)):
                run_post_safe()
            else:
                print(f"  [{t}] היום מפרסמים בשעה אחרת – מדלג")
        scheduler.add_job(job, CronTrigger(hour=h, minute=m), id=f"fb_{idx}", replace_existing=True)

    today_slot = times[datetime.now().date().toordinal() % len(times)]
    print(f"  פוסט אחד ביום. היום בשעה {today_slot}. שעות: {', '.join(times)}  [Q לעצירה]")
    keyboard.add_hotkey("q", lambda: scheduler.shutdown(wait=False))
    try: scheduler.start()
    except: pass
    print("הבוט נעצר.")
