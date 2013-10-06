# -*- coding: utf-8 -*-

from flask import Flask, g
from flask.ext.babel import Babel
from flask.ext.sqlalchemy import SQLAlchemy
from .sessions import MySessionInterface


app = Flask(__name__)
app.config.from_object('config')
babel = Babel(app)
db = SQLAlchemy(app)
app.session_interface = MySessionInterface(db.engine, db.metadata)

from . import views
from . import models

