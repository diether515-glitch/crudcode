"""
Database Rescue - Chapter 4 CRUD Mini System
Team: Wonder Pets | Case: First Step Rural Bank | Table: Borrower

Run:   python app.py            (then open http://127.0.0.1:5000)
Reset: python app.py --reset    (rebuilds the database from database.sql)

Every SQL statement uses ? placeholders (parameterized / prepared statements),
so user input is never joined into the SQL text.
"""
import os
import re
import sqlite3
import sys
from datetime import date, datetime

from flask import (Flask, flash, g, redirect, render_template, request,
                   url_for)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("BORROWER_DB", os.path.join(BASE_DIR, "borrowers.db"))
SCHEMA_PATH = os.path.join(BASE_DIR, "database.sql")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "wonder-pets-classroom-demo")

ID_TYPES = ["PhilSys ID", "Driver's License", "Voter's ID", "SSS ID",
            "UMID", "Postal ID", "PRC ID", "Passport"]
FIELDS = ["FirstName", "MiddleName", "LastName", "BirthDate", "ContactNo",
          "Address", "GovIDType", "GovIDNo"]

# ---------------------------------------------------------------- database
def init_db(reset=False):
    """Create the database from database.sql when it does not exist yet."""
    if reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    if not os.path.exists(DB_PATH):
        con = sqlite3.connect(DB_PATH)
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            con.executescript(f.read())
        con.commit()
        con.close()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ------------------------------------------------------------- validation
NAME_RE = re.compile(r"^[^\W\d_]+(?:[ .'\-]+[^\W\d_]+)*\.?$")
MOBILE_RE = re.compile(r"^(09\d{9}|\+639\d{9})$")
GOVID_RE = re.compile(r"^[A-Za-z0-9\-/]+$")


def clean(value):
    """Trim and collapse repeated spaces."""
    return " ".join((value or "").split())


def age_on(born, today):
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def validate(form, db, exclude_id=-1):
    """Return (cleaned_values, errors). exclude_id lets Update ignore itself."""
    v = {
        "FirstName": clean(form.get("FirstName")),
        "MiddleName": clean(form.get("MiddleName")),
        "LastName": clean(form.get("LastName")),
        "BirthDate": clean(form.get("BirthDate")),
        "ContactNo": re.sub(r"[ \-]", "", form.get("ContactNo", "")),
        "Address": clean(form.get("Address")),
        "GovIDType": clean(form.get("GovIDType")),
        "GovIDNo": clean(form.get("GovIDNo")).upper(),
    }
    e = {}

    for key, label in (("FirstName", "First name"), ("LastName", "Last name")):
        if not v[key]:
            e[key] = f"{label} is required."
        elif len(v[key]) < 2 or len(v[key]) > 50:
            e[key] = f"{label} must be 2 to 50 characters."
        elif not NAME_RE.match(v[key]):
            e[key] = f"{label} may contain letters, spaces, hyphens, apostrophes, and periods only."
    if v["MiddleName"] and (len(v["MiddleName"]) > 50 or not NAME_RE.match(v["MiddleName"])):
        e["MiddleName"] = "Middle name may contain letters only (up to 50 characters)."

    if not v["BirthDate"]:
        e["BirthDate"] = "Birth date is required."
    else:
        try:
            born = datetime.strptime(v["BirthDate"], "%Y-%m-%d").date()
            today = date.today()
            if born > today:
                e["BirthDate"] = "Birth date cannot be in the future."
            elif age_on(born, today) < 18:
                e["BirthDate"] = "Borrower must be at least 18 years old."
            elif age_on(born, today) > 100:
                e["BirthDate"] = "Please check the birth date (age is over 100)."
        except ValueError:
            e["BirthDate"] = "Birth date must be a valid date (YYYY-MM-DD)."

    if not v["ContactNo"]:
        e["ContactNo"] = "Contact number is required."
    elif not MOBILE_RE.match(v["ContactNo"]):
        e["ContactNo"] = "Use a Philippine mobile number: 09XXXXXXXXX or +639XXXXXXXXX."

    if not v["Address"]:
        e["Address"] = "Address is required."
    elif not 10 <= len(v["Address"]) <= 150:
        e["Address"] = "Address must be 10 to 150 characters."

    if v["GovIDType"] not in ID_TYPES:
        e["GovIDType"] = "Choose a government ID type from the list."

    if not v["GovIDNo"]:
        e["GovIDNo"] = "Government ID number is required."
    elif not 5 <= len(v["GovIDNo"]) <= 30 or not GOVID_RE.match(v["GovIDNo"]):
        e["GovIDNo"] = "ID number must be 5 to 30 characters (letters, numbers, - or /)."

    # Duplicate checks (the Symptom 1 fix). Only run when the basics are valid.
    if "GovIDType" not in e and "GovIDNo" not in e:
        dup = db.execute(
            "SELECT BorrowerID FROM Borrower "
            "WHERE GovIDType = ? AND UPPER(GovIDNo) = ? AND BorrowerID != ?",
            (v["GovIDType"], v["GovIDNo"], exclude_id)).fetchone()
        if dup:
            e["GovIDNo"] = f"This {v['GovIDType']} number is already registered (Borrower #{dup['BorrowerID']})."
    if not ({"FirstName", "LastName", "BirthDate"} & set(e)):
        dup = db.execute(
            "SELECT BorrowerID FROM Borrower "
            "WHERE LOWER(FirstName) = LOWER(?) AND LOWER(LastName) = LOWER(?) "
            "AND BirthDate = ? AND BorrowerID != ?",
            (v["FirstName"], v["LastName"], v["BirthDate"], exclude_id)).fetchone()
        if dup:
            e["LastName"] = f"A borrower with the same name and birth date already exists (Borrower #{dup['BorrowerID']})."
    return v, e


# ------------------------------------------------------------------ filters
@app.template_filter("fmtdate")
def fmtdate(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%b %d, %Y")
    except (TypeError, ValueError):
        return value or ""


# ------------------------------------------------------------------- READ
SORTS = {
    "id": "BorrowerID {d}",
    "name": "LastName {d}, FirstName {d}",
    "birth": "BirthDate {d}, BorrowerID {d}",
    "registered": "DateRegistered {d}, BorrowerID {d}",
}
SEARCH_COLUMNS = ["FirstName", "MiddleName", "LastName", "Address",
                  "GovIDNo", "ContactNo"]


def like_escape(text):
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@app.route("/")
def index():
    db = get_db()
    q = clean(request.args.get("q"))
    id_type = request.args.get("id_type", "")
    sort = request.args.get("sort", "id")
    direction = request.args.get("dir", "asc")
    if sort not in SORTS:
        sort = "id"
    if direction not in ("asc", "desc"):
        direction = "asc"

    where, params = [], []
    for token in q.split()[:6]:               # every word must match somewhere
        like = "%" + like_escape(token) + "%"
        cols = " OR ".join(f"{c} LIKE ? ESCAPE '\\'" for c in SEARCH_COLUMNS)
        where.append(f"({cols} OR CAST(BorrowerID AS TEXT) = ?)")
        params += [like] * len(SEARCH_COLUMNS) + [token]
    if id_type in ID_TYPES:
        where.append("GovIDType = ?")
        params.append(id_type)

    sql = "SELECT * FROM Borrower"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY " + SORTS[sort].format(d=direction.upper())   # whitelisted

    rows = db.execute(sql, params).fetchall()
    total = db.execute("SELECT COUNT(*) FROM Borrower").fetchone()[0]
    highlight = request.args.get("highlight", type=int)
    return render_template("list.html", rows=rows, total=total, q=q,
                           id_type=id_type, sort=sort, direction=direction,
                           id_types=ID_TYPES, highlight=highlight)


# ----------------------------------------------------------------- CREATE
@app.route("/add", methods=["GET", "POST"])
def add():
    db = get_db()
    values, errors = {}, {}
    if request.method == "POST":
        values, errors = validate(request.form, db)
        if not errors:
            try:
                cur = db.execute(
                    "INSERT INTO Borrower (FirstName, MiddleName, LastName, BirthDate, "
                    "ContactNo, Address, GovIDType, GovIDNo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (values["FirstName"], values["MiddleName"] or None, values["LastName"],
                     values["BirthDate"], values["ContactNo"], values["Address"],
                     values["GovIDType"], values["GovIDNo"]))
                db.commit()
            except sqlite3.IntegrityError:
                errors["GovIDNo"] = "This borrower is already registered."
            else:
                flash(f"Borrower #{cur.lastrowid} ({values['FirstName']} {values['LastName']}) "
                      "was added successfully.", "success")
                return redirect(url_for("index", highlight=cur.lastrowid))
        flash("The borrower was NOT saved. Please fix the errors below.", "error")
    return render_template("form.html", mode="add", values=values, errors=errors,
                           id_types=ID_TYPES, borrower=None)


# ----------------------------------------------------------------- UPDATE
@app.route("/edit/<int:borrower_id>", methods=["GET", "POST"])
def edit(borrower_id):
    db = get_db()
    borrower = db.execute("SELECT * FROM Borrower WHERE BorrowerID = ?",
                          (borrower_id,)).fetchone()
    if borrower is None:
        flash(f"Borrower #{borrower_id} was not found.", "error")
        return redirect(url_for("index"))

    errors = {}
    values = {k: (borrower[k] or "") for k in FIELDS}     # pre-fill current values
    if request.method == "POST":
        # BorrowerID and DateRegistered are never read from the form.
        values, errors = validate(request.form, db, exclude_id=borrower_id)
        if not errors:
            try:
                db.execute(
                    "UPDATE Borrower SET FirstName = ?, MiddleName = ?, LastName = ?, "
                    "BirthDate = ?, ContactNo = ?, Address = ?, GovIDType = ?, GovIDNo = ? "
                    "WHERE BorrowerID = ?",
                    (values["FirstName"], values["MiddleName"] or None, values["LastName"],
                     values["BirthDate"], values["ContactNo"], values["Address"],
                     values["GovIDType"], values["GovIDNo"], borrower_id))
                db.commit()
            except sqlite3.IntegrityError:
                errors["GovIDNo"] = "This borrower is already registered."
            else:
                flash(f"Borrower #{borrower_id} ({values['FirstName']} {values['LastName']}) "
                      "was updated successfully.", "success")
                return redirect(url_for("index", highlight=borrower_id))
        flash("The changes were NOT saved. Please fix the errors below.", "error")
    return render_template("form.html", mode="edit", values=values, errors=errors,
                           id_types=ID_TYPES, borrower=borrower)


# ----------------------------------------------------------------- DELETE
@app.route("/delete/<int:borrower_id>", methods=["GET", "POST"])
def delete(borrower_id):
    db = get_db()
    borrower = db.execute("SELECT * FROM Borrower WHERE BorrowerID = ?",
                          (borrower_id,)).fetchone()
    if borrower is None:
        flash(f"Borrower #{borrower_id} was not found. Nothing was deleted.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":                          # only after confirming
        db.execute("DELETE FROM Borrower WHERE BorrowerID = ?", (borrower_id,))
        db.commit()
        flash(f"Borrower #{borrower_id} ({borrower['FirstName']} {borrower['LastName']}) "
              "was deleted.", "success")
        return redirect(url_for("index"))
    return render_template("confirm_delete.html", b=borrower)   # GET = ask first


# ------------------------------------------------------------------- main
init_db()

if __name__ == "__main__":
    if "--reset" in sys.argv:
        init_db(reset=True)
        print("Database rebuilt from database.sql")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=False)
