# -*- coding: utf-8 -*-

from flask import Flask, g, current_app, request
from flask.ext.babel import Babel
from flask.ext.sqlalchemy import SQLAlchemy, event
from flask.ext.mail import Mail
from werkzeug.contrib.cache import NullCache
from .sessions import MySessionInterface


babel = Babel()
db = SQLAlchemy()
sess = MySessionInterface(db)
cache = NullCache()
mail = Mail()

def get_locale():
    return request.accept_languages.best_match(current_app.config['LANGUAGES'].keys())


def create_app(config={}):
    global babel, db, mail, sess
    app = Flask(__name__)
    app.config.from_object('ffdnispdb.default_settings')
    app.config.from_envvar('FFDNISPDB_SETTINGS', True)
    if isinstance(config, dict):
        app.config.update(config)
    else:
        app.config.from_object(config)
    babel.init_app(app)
    babel.localeselector(get_locale)
    db.init_app(app)

    with app.app_context():
        @event.listens_for(db.engine, "connect")
        def connect(sqlite, connection_rec):
            sqlite.enable_load_extension(True)
            sqlite.execute('select load_extension("libspatialite.so")')
            sqlite.enable_load_extension(False)

    app.session_interface = sess
    mail.init_app(app)

    from .views import ispdb
    app.register_blueprint(ispdb)
    return app


from . import models

