import os
import datetime

from os import path, walk
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///tool.db")

@app.route('/')
@login_required
def index():
    user_id = session["user_id"]
    entry_id = db.execute("SELECT entry_id FROM entries WHERE DATE(entry_date) = CURRENT_DATE AND user_id = :user_id ", user_id=user_id)

    if not entry_id:
        db.execute("INSERT INTO entries (user_id, entry_date) VALUES (:user_id, :entry_date)", user_id=session["user_id"], entry_date=datetime.datetime.now())
        entry_id = db.execute("SELECT entry_id FROM entries WHERE DATE(entry_date) = CURRENT_DATE AND user_id = :user_id ", user_id=user_id)
    entry_id = entry_id[0].get('entry_id')
    session["entry_id"] = entry_id
    entry_details = db.execute("SELECT * FROM entries WHERE entry_id = :entry_id", entry_id=entry_id)
    session['entry_details'] = entry_details
    return render_template("index.html")

@app.route('/edit/<id>', methods=["GET", "POST"])
@login_required
def edit(id):

    if request.method == "POST":
        goal = request.form.get("goal")
        goal = goal or None
        issue = request.form.get("issue")
        issue = issue or None
        reflection = request.form.get("reflection")
        reflection = reflection or None
        mood = request.form.get("mood")
        mood = mood or None
        user_id = session["user_id"]
        entry_id = id

        db.execute("UPDATE entries SET goal=:goal, issue=:issue, reflection=:reflection, mood=:mood WHERE user_id=:user_id AND entry_id=:entry_id", goal=goal, issue=issue, reflection=reflection, mood=mood, user_id=user_id, entry_id=entry_id)
        return redirect("/")


    entry_id = id
    user_id = session["user_id"]
    id_exists = db.execute("SELECT * FROM entries WHERE EXISTS (SELECT * FROM entries WHERE entry_id = :entry_id AND user_id=:user_id)", entry_id=entry_id, user_id=user_id)
    if not id_exists:
        return apology("you have no access", 403)
    entry_details = db.execute("SELECT * FROM entries WHERE entry_id = :entry_id AND user_id=:user_id", entry_id=entry_id, user_id=user_id)
    goal=entry_details[0].get('goal')
    issue=entry_details[0].get('issue')
    reflection=entry_details[0].get('reflection')
    mood=entry_details[0].get('mood')
    return render_template("edit.html", goal=goal, issue=issue, reflection=reflection, mood=mood, entry_id=entry_id)


@app.route('/goals', methods=["GET", "POST"])
@login_required
def goals():

    if request.method == "POST":
        goal = request.form.get("goal").strip()
        user_id = session["user_id"]
        entry_details = session.get('entry_details', None)

        if not goal:
            return redirect("/")

        else:
            db.execute("UPDATE entries SET goal=:goal WHERE user_id=:user_id AND entry_id=:entry_id", goal=goal, user_id=user_id, entry_id=entry_details[0].get('entry_id'))
            return redirect("/")

    entry_details = session.get('entry_details', None)
    return render_template("goals.html", goal=entry_details[0].get('goal'))

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("email"):
            return apology("must provide email", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE email = :email",
                          email=request.form.get("email"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid email and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["user_id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    #forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("email"):
            return apology("must provide e-mail address", 403)

        elif not request.form.get("lastname"):
            return apology("must provide lastname", 403)

        elif not request.form.get("firstname"):
            return apology("must provide firstname", 403)
        # Ensure password was submitted
        elif not request.form.get("password1") and request.form.get("password2"):
            return apology("must provide password", 403)

        elif request.form.get("password1") != request.form.get("password2"):
            return apology("passwords have to be the same")

        # Query database for username
        db.execute("INSERT INTO users (email, first_name, last_name, hash) VALUES (:email, :first_name, :last_name, :hash)", email=request.form.get("email"), first_name=request.form.get("firstname"), last_name=request.form.get("lastname"), hash=generate_password_hash(request.form.get("password1")))
        rows = db.execute("SELECT * FROM users WHERE email = :email", email=request.form.get("email"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["user_id"]

        # Redirect user to home page
        return redirect("/login")

    else:
        return render_template("register.html")

@app.route('/history')
@login_required
def history():
    user_id = session["user_id"]
    entries = db.execute("SELECT * FROM entries WHERE user_id = :user_id", user_id=user_id)
    for entry in entries:
        entry["entry_date"] = datetime.datetime.strptime(entry["entry_date"], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%y')
    print("ENTRIES:", entries)
    return render_template("history.html", entries=entries)

@app.route('/issue', methods=["GET", "POST"])
@login_required
def issue():

    if request.method == "POST":
        issue = request.form.get("issue")
        print("ISSUE", issue)
        user_id = session["user_id"]
        entry_details = session.get('entry_details', None)

        if not issue:
            return redirect("/reflection")

        else:
            db.execute("UPDATE entries SET issue=:issue WHERE user_id=:user_id AND entry_id=:entry_id", issue=issue, user_id=user_id, entry_id=entry_details[0].get('entry_id'))
            return redirect("/reflection")

    entry_id = session.get('entry_id', None)
    entry_details = db.execute("SELECT * FROM entries WHERE entry_id = :entry_id", entry_id=entry_id)
    return render_template("issue.html", issue=entry_details[0].get('issue'))

@app.route('/reflection', methods=["GET", "POST"])
@login_required
def reflection():

    if request.method == "POST":
        reflection = request.form.get("reflection")
        user_id = session["user_id"]
        entry_details = session.get('entry_details', None)

        if not reflection:
            return redirect("/mood")

        else:
            db.execute("UPDATE entries SET reflection=:reflection WHERE user_id=:user_id AND entry_id=:entry_id", reflection=reflection, user_id=user_id, entry_id=entry_details[0].get('entry_id'))
            return redirect("/mood")


    entry_id = session.get('entry_id', None)
    entry_details = db.execute("SELECT * FROM entries WHERE entry_id = :entry_id", entry_id=entry_id)
    return render_template("reflection.html", reflection=entry_details[0].get('reflection'))

@app.route('/mood', methods=["GET", "POST"])
@login_required
def mood():

    if request.method == "POST":
        mood = request.form.get("mood")
        print("mood is:", mood)
        user_id = session["user_id"]
        entry_details = session.get('entry_details', None)

        if not reflection:
            return redirect("/")

        else:
            db.execute("UPDATE entries SET mood=:mood WHERE user_id=:user_id AND entry_id=:entry_id", mood=mood, user_id=user_id, entry_id=entry_details[0].get('entry_id'))
            return redirect("/")


    entry_id = session.get('entry_id', None)
    entry_details = db.execute("SELECT * FROM entries WHERE entry_id = :entry_id", entry_id=entry_id)
    return render_template("mood.html", mood=entry_details[0].get('mood'))




def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
