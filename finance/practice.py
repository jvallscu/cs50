
from cs50 import SQL

from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

symbol = "MVIS"
stock = lookup(symbol)




stock_symbol = stock.get("symbol")
print(str(stock_symbol))

symbols_dict = db.execute("SELECT DISTINCT symbol FROM shares_log")

print(symbols_dict[0].get("symbol"))
symbols_list = []
for i in range(len(symbols_list)):
    symbols_list = symbols_list.append(symbols_dict[i].get("symbol"))

print(symbols_list)
