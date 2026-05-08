## Below is the python for the CSET-180 Final ##

## Importing flask and other modules ##
from flask import Flask
from flask import render_template, request, redirect, session, url_for
from sqlalchemy import create_engine, text
import random

## Setting up Flask / Routes ##
app = Flask(__name__)
app.config["SECRET_KEY"] = "p455k3y"

con_str = "mysql://root:cset155@localhost/ecomdb"
engine = create_engine(con_str, echo = True)
conn = engine.connect()

## App Routes ##

# Route for LogIn #
@app.route("/")
def index():
    return redirect(url_for('login'))

@app.route("/login")
def login():
    return render_template('login.html')

@app.route("/signup")
def signup():
    return render_template('signup.html')

# Route for Products/Store
@app.route("/store")
def store():
    return render_template('store.html')

# Route for myaccount
@app.route("/myaccount")
def myaccount():
    return render_template('myaccount.html')


# Route for myorders
@app.route("/myorders")
def myorders():
    return render_template('myorders.html')

# Route for cart
@app.route("/cart")
def cart():
    return render_template('cart.html')

# Route for vendors
@app.route("/vendor")
def vendor():
    return render_template('vendor.html')

# Route for admin
@app.route("/admin")
def admin():
    return render_template('admin.html')

if __name__ == "__main__":
    app.run(debug=True)
