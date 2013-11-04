# -*- coding: utf-8 -*-

from flask import Flask, g
from flask.ext.babel import Babel
from flask.ext.sqlalchemy import SQLAlchemy, event
from flask.ext.mail import Mail
from werkzeug.contrib.cache import NullCache
from .sessions import MySessionInterface


app = Flask(__name__)
app.config.from_object('config')
babel = Babel(app)
db = SQLAlchemy(app)
app.session_interface = MySessionInterface(db)
cache = NullCache()
mail = Mail(app)

@event.listens_for(db.engine, "connect")
def connect(sqlite, connection_rec):
    sqlite.enable_load_extension(True)
    sqlite.execute('select load_extension("libspatialite.so")')
    sqlite.enable_load_extension(False)

from . import views
from . import models

