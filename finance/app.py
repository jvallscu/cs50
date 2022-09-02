import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

from datetime import datetime

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
#if not os.environ.get("API_KEY"):
#    raise RuntimeError("API_KEY not set")



@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET" , "POST"])
@login_required
def index():
    """Show portfolio of stocks"""

    list = []
    stock_total = 0
    symbols_list = db.execute("SELECT DISTINCT symbol, company_name FROM shares_log")

    #iterates through unique stock symbols
    for i in range(len(symbols_list)):
        share_count = db.execute("SELECT SUM(share_count) FROM shares_log WHERE symbol= (?)", symbols_list[i].get("symbol"))
        stock = lookup(symbols_list[i].get("symbol"))
        price = stock.get("price")
        num_shares = share_count[0].get('SUM(share_count)')
        list.append({'Symbol': symbols_list[i].get("symbol"), 'Name': symbols_list[i].get("company_name"), 'Shares': num_shares, 'Price': price, 'TOTAL': usd(num_shares * price)})
        stock_total = stock_total + (num_shares * price)
    cash = db.execute("SELECT cash FROM users WHERE id = (?)", session["user_id"])
    print(list)

    stock_total = cash[0].get("cash") + stock_total

    if request.method == "POST":
        return render_template("cash.html")

    return render_template("index.html", list=list, cash=usd(cash[0].get("cash")), stock_total=usd(stock_total))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    symbol = request.form.get("symbol")

    if request.method == "GET":
        return render_template("buy.html")
    if request.method == "POST":
        #Check for valid stock entry
        if not request.form.get("symbol") or lookup(symbol) == None:
            return apology("Stock not found", 403)
        if int(request.form.get("shares")) < 0:
            return apology("No shorties allowed", 403)

        stock = lookup(symbol)
        stock_name = stock.get("name")
        stock_symbol = stock.get("symbol")
        stock_price = stock.get("price")
        price = float(request.form.get("shares")) * stock_price


        cash = db.execute("SELECT cash FROM users WHERE id = (?)", session["user_id"])

        #Checks that user is not spending more funds than they have
        if price > cash[0].get("cash"):
            return apology("You don't have enough money!!")

        updated_cash = cash[0].get("cash") - price
        db.execute("UPDATE users SET cash = (?) WHERE id = (?)", updated_cash, session["user_id"])

        # Gets current time and date
        now = datetime.now()
        dt_str = now.strftime("%Y/%m/%d %H:%M:%S")

        #Inserts transaction into the log
        db.execute("INSERT INTO shares_log (user_id, symbol, price, share_count, time, company_name) VALUES(?, ?, ?, ?, ?, ?)", session["user_id"], str(stock_symbol), stock_price, request.form.get("shares"), str(dt_str), str(stock_name))

        return render_template("buy.html", price=cash, new_cash=updated_cash)


    return apology("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    history = db.execute("SELECT * FROM shares_log WHERE user_id = (?) ORDER BY time DESC", session["user_id"])

    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "GET":
        return render_template("quote.html")
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if lookup(symbol) == None:
            return apology("Stock not found", 403)

        stock = lookup(symbol)
        name = stock.get("name")
        price = stock.get("price")
        s_symbol = stock.get("symbol")

        return render_template("quoted.html", name=name, price=usd(price), symbol=s_symbol)


    return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():

    """Register user"""

    if request.method == "GET":
        return render_template("register.html")

    if request.method == "POST":
        # Ensure user submitted a username
        if not request.form.get("username"):
            return apology("must provide username", 403)
        # Ensure user submitted a password
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Check that username is already not in that database...
        user_db = db.execute("SELECT username from users")
        user = request.form.get("username")

        for username in user_db:
            if username.get("username") == user:
                return apology("ALREADY IN SYSTEM", 403)

        # Make sure that user types in password twice and values match
        if request.form.get("password") == request.form.get("confirmation"):
            # Add user to database
            hash = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", user, hash)

            rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
            session["user_id"] = rows[0]["id"]

            return apology("SUCCESS", 403)
        else:
            return apology("You did not type in your password twice correctly", 403)

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "GET":
        symbols = db.execute("SELECT DISTINCT symbol FROM shares_log")
        #print(symbols)
        return render_template("sell.html", symbols=symbols)

    if request.method == "POST":
        #Check to see if user chose a stock
        if request.form.get("symbol") == None:
            return apology("You didn't choose a stock")

        # A user can't sell 0 stock, like why?

        if int(request.form.get("shares")) <= 0 or request.form.get("shares") == None:
            return apology("You didn't choose a proper quantity")

        symbol = request.form.get("symbol")
        share_count = db.execute("SELECT SUM(share_count) FROM shares_log WHERE symbol= (?)", symbol)
        shares = share_count[0].get('SUM(share_count)') - int(request.form.get("shares"))

        if shares <= 0:
            return apology("You don't have enough shares to sell")

         # Gets current time and date
        now = datetime.now()
        dt_str = now.strftime("%Y/%m/%d %H:%M:%S")


        stock = lookup(symbol)
        stock_price = stock.get("price")
        stock_name = stock.get("name")



        cash = db.execute("SELECT cash FROM users WHERE id = (?)", session["user_id"])
        price = float(request.form.get("shares")) * stock_price
        updated_cash = cash[0].get("cash") + price
        db.execute("UPDATE users SET cash = (?) WHERE id = (?)", updated_cash, session["user_id"])


        db.execute("INSERT INTO shares_log (user_id, symbol, price, share_count, time, company_name) VALUES(?, ?, ?, ?, ?, ?)", session["user_id"], symbol, stock_price, (0 - int(request.form.get("shares"))), str(dt_str), str(stock_name))


        print(request.form.get("symbol"))

        return redirect("/")


    return apology("TODO")



@app.route("/cash", methods=["GET" , "POST"])
@login_required
def cash():
    """Add funds to your wallet"""
    if request.method == "POST":


        updated_cash = request.form.get("amount")
        cash_list_dict = db.execute("SELECT cash FROM users WHERE id = (?)", session["user_id"])
        cash = cash_list_dict[0].get("cash")
        updated_cash = float(updated_cash) + cash

        db.execute("UPDATE users SET cash = (?) WHERE id = (?)", updated_cash, session["user_id"])

        return redirect("/")
