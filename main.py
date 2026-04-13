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