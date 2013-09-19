# -*- coding: utf-8 -*-

from flask import Flask, g
from flask.ext.babel import Babel
from flask.ext.sqlalchemy import SQLAlchemy
import sqlite3

app = Flask(__name__)
app.config.from_object('config')
babel = Babel(app)
db = SQLAlchemy(app)


from . import views
from . import models

