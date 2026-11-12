"""
Drives the running app in a real browser and saves screenshots to /screenshots.
Optional helper for the report (needs: pip install playwright && playwright install chromium).
Uses a temporary database, so your real borrowers.db is untouched.
"""
import os
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "screenshots")
DB = "/tmp/shots.db"
PORT = 5057
URL = f"http://127.0.0.1:{PORT}"

if os.path.exists(DB):
    os.remove(DB)
os.makedirs(OUT, exist_ok=True)
env = dict(os.environ, BORROWER_DB=DB, PORT=str(PORT))
server = subprocess.Popen([sys.executable, os.path.join(ROOT, "app.py")], env=env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(URL, timeout=1)
            break
        except Exception:
            time.sleep(0.2)

    def shot(page, name):
        page.screenshot(path=os.path.join(OUT, name + ".png"), full_page=True)
        print("saved", name)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 700}, device_scale_factor=1.5)

        # READ - full list (also the "before" for Create)
        page.goto(URL)
        shot(page, "01_read_list_all")

        # CREATE - invalid submit first, then a valid record
        page.goto(URL + "/add")
        page.click("button.primary")
        shot(page, "02_create_invalid")

        page.goto(URL + "/add")
        page.fill("input[name=FirstName]", "Angelica")
        page.fill("input[name=MiddleName]", "Rivera")
        page.fill("input[name=LastName]", "Cruz")
        page.fill("input[name=BirthDate]", "1993-08-19")
        page.fill("input[name=ContactNo]", "09291230013")
        page.fill("input[name=Address]", "Brgy. Dolores, Capas, Tarlac")
        page.select_option("select[name=GovIDType]", "PhilSys ID")
        page.fill("input[name=GovIDNo]", "8812-3345-6671-0013")
        shot(page, "03_create_form_filled")
        page.click("button.primary")
        shot(page, "04_create_after_list")

        # READ - search, no match, filter + sort
        page.goto(URL)
        page.fill("input[name=q]", "dela cruz")
        page.click("form.toolbar button[type=submit]")
        shot(page, "05_read_search")

        page.goto(URL)
        page.fill("input[name=q]", "zzzz")
        page.click("form.toolbar button[type=submit]")
        shot(page, "06_read_no_match")

        page.goto(URL)
        page.select_option("select[name=id_type]", "PhilSys ID")
        page.select_option("select[name=sort]", "birth")
        page.click("form.toolbar button[type=submit]")
        shot(page, "07_read_filter_sort")

        # UPDATE - Borrower #3: open pre-filled form, invalid try, valid save
        page.goto(URL)
        page.click("tr:has(td:text-is('3')) a.btn:text('Edit')")
        shot(page, "08_update_form_prefilled")

        page.fill("input[name=LastName]", "")
        page.fill("input[name=ContactNo]", "abc")
        page.click("button.primary")
        shot(page, "09_update_invalid")

        page.goto(URL + "/edit/3")
        page.fill("input[name=ContactNo]", "09191239999")
        page.fill("input[name=Address]", "Brgy. Poblacion East, Gerona, Tarlac")
        page.click("button.primary")
        shot(page, "10_update_after_list")

        # DELETE - Borrower #5: confirmation, then confirmed
        page.goto(URL)
        page.click("tr:has(td:text-is('5')) a.btn:text('Delete')")
        shot(page, "11_delete_confirm")
        page.click("button.danger-solid")
        shot(page, "12_delete_after_list")
        browser.close()
finally:
    server.terminate()
    if os.path.exists(DB):
        os.remove(DB)
