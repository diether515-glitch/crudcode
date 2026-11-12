"""
Chapter 4 test cases for the Borrower CRUD system.

Run from the project folder:   python tests/run_tests.py
Uses a temporary copy of the database, so your real borrowers.db is untouched.
Prints each test case with its actual result and saves them to tests/test_results.json.
"""
import json
import os
import re
import sqlite3
import sys
import tempfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
TMP_DB = os.path.join(tempfile.gettempdir(), "borrower_test.db")
os.environ["BORROWER_DB"] = TMP_DB

import app as bank  # noqa: E402  (must come after BORROWER_DB is set)

client = bank.app.test_client()
RESULTS = []


# ------------------------------------------------------------------ helpers
def fresh():
    bank.init_db(reset=True)


def db(sql, params=()):
    con = sqlite3.connect(TMP_DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(sql, params).fetchall()
    con.close()
    return rows


def count():
    return db("SELECT COUNT(*) AS n FROM Borrower")[0]["n"]


def flashes(html):
    return [re.sub(r"\s+", " ", m).strip()
            for m in re.findall(r'class="flash [a-z]+"[^>]*>(.*?)</div>', html, re.S)]


def errors(html):
    return re.findall(r'<span class="err">(.*?)</span>', html)


def ids_in(html):
    return [int(x) for x in re.findall(r'<tr class="[^"]*">\s*<td>(\d+)</td>', html)]


def case(code, op, title, test_input, expected):
    def wrap(fn):
        fresh()
        try:
            ok, actual = fn()
        except Exception as exc:  # a crash is a failed test
            ok, actual = False, f"Program error: {exc!r}"
        RESULTS.append({"id": code, "operation": op, "test": title,
                        "input": test_input, "expected": expected,
                        "actual": actual, "result": "Pass" if ok else "FAIL"})
        return fn
    return wrap


NEW = {"FirstName": "Angelica", "MiddleName": "Rivera", "LastName": "Cruz",
       "BirthDate": "1993-08-19", "ContactNo": "09291230013",
       "Address": "Brgy. Dolores, Capas, Tarlac", "GovIDType": "PhilSys ID",
       "GovIDNo": "8812-3345-6671-0013"}

# ------------------------------------------------------------------- CREATE
@case("C1", "Create", "Add a valid borrower",
      "All fields filled with valid data (Angelica Rivera Cruz, PhilSys ID 8812-...-0013)",
      "Record saved, ID generated, DateRegistered defaults to today, success message, count 12 to 13")
def _():
    r = client.post("/add", data=NEW, follow_redirects=True)
    row = db("SELECT * FROM Borrower WHERE GovIDNo = ?", (NEW["GovIDNo"],))
    ok = (count() == 13 and len(row) == 1 and row[0]["BorrowerID"] == 13
          and row[0]["DateRegistered"] == date.today().isoformat()
          and any("added successfully" in f for f in flashes(r.get_data(as_text=True))))
    return ok, (f"Saved as Borrower #{row[0]['BorrowerID']}, DateRegistered {row[0]['DateRegistered']}, "
                f"count 12 to {count()}; message: \"{flashes(r.get_data(as_text=True))[0]}\"") if row else "Not saved"


@case("C2", "Create", "Submit an empty form", "Every field left blank",
      "Rejected with required-field messages; nothing saved")
def _():
    r = client.post("/add", data={k: "" for k in NEW})
    errs = errors(r.get_data(as_text=True))
    return (count() == 12 and len(errs) >= 6), f"Rejected with {len(errs)} messages (e.g. \"{errs[0]}\"); count stayed {count()}"


@case("C3", "Create", "Invalid values in several fields",
      "First name \"J0hn\", birth date 10 years ago, contact no. \"12345\"",
      "Rejected with a message for each bad field; nothing saved")
def _():
    bad = dict(NEW, FirstName="J0hn", ContactNo="12345",
               BirthDate=date.today().replace(year=date.today().year - 10).isoformat())
    r = client.post("/add", data=bad)
    errs = errors(r.get_data(as_text=True))
    ok = count() == 12 and len(errs) == 3
    return ok, f"Rejected; {len(errs)} messages: " + " | ".join(errs)


@case("C4", "Create", "Duplicate government ID",
      "New person but PhilSys ID 4521-8830-1127-0001 (already used by Borrower #1)",
      "Rejected with a duplicate-ID message; nothing saved")
def _():
    dup = dict(NEW, GovIDNo="4521-8830-1127-0001")
    r = client.post("/add", data=dup)
    errs = errors(r.get_data(as_text=True))
    return (count() == 12 and any("already registered" in e for e in errs)), f"Rejected: \"{errs[0]}\"; count stayed {count()}"


@case("C5", "Create", "Same name and birth date, different ID",
      "Maria Santos, born 1985-03-12, with a new PhilSys ID number",
      "Rejected as a duplicate borrower; nothing saved")
def _():
    dup = dict(NEW, FirstName="Maria", LastName="Santos", BirthDate="1985-03-12", GovIDNo="9999-0000-1111-2222")
    r = client.post("/add", data=dup)
    errs = errors(r.get_data(as_text=True))
    return (count() == 12 and any("same name and birth date" in e for e in errs)), f"Rejected: \"{errs[0]}\"; count stayed {count()}"


# --------------------------------------------------------------------- READ
@case("R1", "Read", "List all saved records", "Open the home page with no search",
      "All 12 records from the database are shown in a table")
def _():
    html = client.get("/").get_data(as_text=True)
    ids = ids_in(html)
    return (ids == list(range(1, 13))), f"Table shows {len(ids)} rows (IDs {ids[0]} to {ids[-1]}); text \"Showing 12 of 12 borrower records\" present: {'Showing <strong>12</strong> of <strong>12</strong>' in html}"


@case("R2", "Read", "Search by name", "Search box: \"dela cruz\"",
      "Only Borrower #2 and #3 are shown")
def _():
    html = client.get("/?q=dela+cruz").get_data(as_text=True)
    ids = ids_in(html)
    return ids == [2, 3], f"Rows returned: IDs {ids}"


@case("R3", "Read", "Filter by government ID type", "Government ID filter: PhilSys ID",
      "Only the four PhilSys ID borrowers (#1, #5, #9, #12) are shown")
def _():
    html = client.get("/?id_type=PhilSys+ID").get_data(as_text=True)
    ids = ids_in(html)
    return ids == [1, 5, 9, 12], f"Rows returned: IDs {ids}"


@case("R4", "Read", "Sort by birth date", "Sort by: Birth date, Ascending",
      "Oldest borrower first (#8, born 1968), youngest last (#12, born 1999)")
def _():
    ids = ids_in(client.get("/?sort=birth&dir=asc").get_data(as_text=True))
    return (ids[0] == 8 and ids[-1] == 12 and len(ids) == 12), f"First row #{ids[0]}, last row #{ids[-1]}, {len(ids)} rows"


@case("R5", "Read", "Search with no match", "Search box: \"zzzz\"",
      "A clear \"No borrowers found\" message, no table rows")
def _():
    html = client.get("/?q=zzzz").get_data(as_text=True)
    return ("No borrowers found" in html and not ids_in(html)), "Message \"No borrowers found for your search or filter.\" displayed; 0 rows"


@case("R6", "Read", "SQL-injection style text in the search box",
      "Search box: ' OR 1=1 --",
      "Treated as plain text (parameterized query): 0 matches, no error, table intact")
def _():
    r = client.get("/", query_string={"q": "' OR 1=1 --"})
    html = r.get_data(as_text=True)
    return (r.status_code == 200 and not ids_in(html) and count() == 12), f"HTTP {r.status_code}; {len(ids_in(html))} rows returned; table still has {count()} records"


# ------------------------------------------------------------------- UPDATE
@case("U1", "Update", "Edit form is pre-filled and ID is locked", "Click Edit on Borrower #3",
      "Current values appear in the form; Borrower ID is shown but cannot be edited")
def _():
    html = client.get("/edit/3").get_data(as_text=True)
    ok = ('value="Rosario"' in html and 'value="Dela Cruz"' in html and 'value="09191230003"' in html
          and 'value="3" readonly disabled' in html and 'name="BorrowerID"' not in html)
    return ok, "First name, last name, contact no. etc. pre-filled for #3; Borrower ID box is read-only/disabled and not a submitted field"


@case("U2", "Update", "Save a valid change", "Borrower #3: contact no. changed to 09191239999, address changed",
      "Only #3 changes; success message; other 11 records unchanged")
def _():
    before = {r["BorrowerID"]: tuple(r) for r in db("SELECT * FROM Borrower")}
    data = {"FirstName": "Rosario", "MiddleName": "", "LastName": "Dela Cruz", "BirthDate": "1990-11-02",
            "ContactNo": "09191239999", "Address": "Brgy. Poblacion East, Gerona, Tarlac",
            "GovIDType": "Voter's ID", "GovIDNo": "7102-0045-8890"}
    r = client.post("/edit/3", data=data, follow_redirects=True)
    after = {r_["BorrowerID"]: tuple(r_) for r_ in db("SELECT * FROM Borrower")}
    changed = [i for i in before if before[i] != after[i]]
    ok = changed == [3] and after[3][5] == "09191239999" and any("updated successfully" in f for f in flashes(r.get_data(as_text=True)))
    return ok, f"Changed record(s): {changed}; new contact no. {after[3][5]}; message: \"{flashes(r.get_data(as_text=True))[0]}\""


@case("U3", "Update", "Invalid change is rejected", "Borrower #3: last name blank, contact no. \"abc\"",
      "Rejected with messages; record #3 keeps its old values")
def _():
    before = tuple(db("SELECT * FROM Borrower WHERE BorrowerID = 3")[0])
    data = {"FirstName": "Rosario", "MiddleName": "", "LastName": "", "BirthDate": "1990-11-02",
            "ContactNo": "abc", "Address": "Brgy. Poblacion, Gerona, Tarlac",
            "GovIDType": "Voter's ID", "GovIDNo": "7102-0045-8890"}
    r = client.post("/edit/3", data=data)
    errs = errors(r.get_data(as_text=True))
    after = tuple(db("SELECT * FROM Borrower WHERE BorrowerID = 3")[0])
    return (before == after and len(errs) == 2), f"Rejected; {len(errs)} messages: " + " | ".join(errs) + "; record #3 unchanged"


@case("U4", "Update", "ID and registration date cannot be tampered with",
      "Edit #3 but also send BorrowerID=99 and DateRegistered=2000-01-01 in the request",
      "Extra fields ignored: ID stays 3, DateRegistered unchanged")
def _():
    before = db("SELECT * FROM Borrower WHERE BorrowerID = 3")[0]
    data = {"BorrowerID": "99", "DateRegistered": "2000-01-01", "FirstName": "Rosario", "MiddleName": "",
            "LastName": "Dela Cruz", "BirthDate": "1990-11-02", "ContactNo": "09191230003",
            "Address": "Brgy. Poblacion, Gerona, Tarlac", "GovIDType": "Voter's ID", "GovIDNo": "7102-0045-8890"}
    client.post("/edit/3", data=data, follow_redirects=True)
    after = db("SELECT * FROM Borrower WHERE BorrowerID = 3")
    none99 = db("SELECT COUNT(*) AS n FROM Borrower WHERE BorrowerID = 99")[0]["n"] == 0
    ok = len(after) == 1 and after[0]["DateRegistered"] == before["DateRegistered"] and none99
    return ok, f"Still Borrower #3 with DateRegistered {after[0]['DateRegistered']}; no record #99 was created"


@case("U5", "Update", "Change to another borrower's government ID", "Borrower #3 given PhilSys ID 4521-8830-1127-0001 (belongs to #1)",
      "Rejected as duplicate; record #3 unchanged")
def _():
    before = tuple(db("SELECT * FROM Borrower WHERE BorrowerID = 3")[0])
    data = {"FirstName": "Rosario", "MiddleName": "", "LastName": "Dela Cruz", "BirthDate": "1990-11-02",
            "ContactNo": "09191230003", "Address": "Brgy. Poblacion, Gerona, Tarlac",
            "GovIDType": "PhilSys ID", "GovIDNo": "4521-8830-1127-0001"}
    r = client.post("/edit/3", data=data)
    errs = errors(r.get_data(as_text=True))
    after = tuple(db("SELECT * FROM Borrower WHERE BorrowerID = 3")[0])
    return (before == after and any("already registered" in e for e in errs)), f"Rejected: \"{errs[0]}\"; record #3 unchanged"


# ------------------------------------------------------------------- DELETE
@case("D1", "Delete", "Confirmation appears before deleting", "Click Delete on Borrower #5",
      "\"Are you sure?\" page with the record details; nothing deleted yet")
def _():
    r = client.get("/delete/5")
    html = r.get_data(as_text=True)
    return ("Are you sure?" in html and "Mendoza" in html and count() == 12), f"Confirmation page shown for #5 (Teresita Garcia Mendoza); count still {count()}"


@case("D2", "Delete", "Confirm the deletion", "On the confirmation page, click \"Yes, delete this borrower\" for #5",
      "Only #5 is removed from the database; list updates immediately; count 12 to 11")
def _():
    before_ids = [r["BorrowerID"] for r in db("SELECT BorrowerID FROM Borrower")]
    r = client.post("/delete/5", follow_redirects=True)
    html = r.get_data(as_text=True)
    after_ids = [r_["BorrowerID"] for r_ in db("SELECT BorrowerID FROM Borrower")]
    expected = [i for i in before_ids if i != 5]
    ok = after_ids == expected and 5 not in ids_in(html) and any("was deleted" in f for f in flashes(html))
    return ok, f"Count 12 to {count()}; #5 missing from DB and from the list; message: \"{flashes(html)[0]}\""


@case("D3", "Delete", "Delete a record that does not exist", "Open /delete/999 and submit",
      "Friendly \"not found\" message, no crash, no data lost")
def _():
    r1 = client.get("/delete/999", follow_redirects=True)
    r2 = client.post("/delete/999", follow_redirects=True)
    msg = flashes(r2.get_data(as_text=True))
    return (r1.status_code == 200 and r2.status_code == 200 and count() == 12 and any("not found" in m for m in msg)), f"HTTP {r2.status_code}; message: \"{msg[0]}\"; count stayed {count()}"


@case("D4", "Delete", "Cancel keeps the record", "Open the confirmation for #7, then choose \"No, cancel\" (back to the list)",
      "Record #7 is still in the database and the list")
def _():
    client.get("/delete/7")
    html = client.get("/").get_data(as_text=True)
    return (7 in ids_in(html) and count() == 12), f"Record #7 still listed; count {count()}"


# ---------------------------------------------------------------- report
if __name__ == "__main__":
    width = 100
    print("=" * width)
    for r in RESULTS:
        print(f"[{r['result']:<4}] {r['id']:<3} {r['operation']:<6} {r['test']}")
        print(f"        Input   : {r['input']}")
        print(f"        Expected: {r['expected']}")
        print(f"        Actual  : {r['actual']}")
    passed = sum(1 for r in RESULTS if r["result"] == "Pass")
    print("=" * width)
    print(f"{passed} of {len(RESULTS)} test cases passed")
    with open(os.path.join(ROOT, "tests", "test_results.json"), "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2, ensure_ascii=False)
    fresh()
    sys.exit(0 if passed == len(RESULTS) else 1)
