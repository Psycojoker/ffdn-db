# -*- coding: utf-8 -*-

from flask import Flask, g
from flask.ext.babel import Babel
from flask.ext.sqlalchemy import SQLAlchemy
import sqlite3

app = Flask(__name__)
app.config.from_object('config')
babel = Babel(app)
db = SQLAlchemy(app)


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

#@app.before_request
def before_request():
    g.db = connect_db()
    #g.db.execute("PRAGMA foreign_keys = ON")

#@app.teardown_request
def teardown_request(exception):
    g.db.close()

def query_db(query, args=(), one=False):
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
        for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()


from . import views
from . import models

