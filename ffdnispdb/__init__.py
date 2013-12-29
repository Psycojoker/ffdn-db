# -*- coding: utf-8 -*-

from flask import Flask, g, current_app, request
from flask.ext.babel import Babel
from flask.ext.sqlalchemy import SQLAlchemy, event
from flask.ext.mail import Mail
from flask.ext.cache import Cache
from .sessions import MySessionInterface


babel = Babel()
db = SQLAlchemy()
sess = MySessionInterface(db)
cache = Cache()
mail = Mail()

def get_locale():
    if request.cookies.get('locale') in current_app.config['LANGUAGES'].keys():
        return request.cookies.get('locale')
    return request.accept_languages.best_match(current_app.config['LANGUAGES'].keys(), 'en')


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
    cache.init_app(app)

    from .views import ispdb
    from .views_api import ispdbapi
    app.register_blueprint(ispdb)
    app.register_blueprint(ispdbapi, url_prefix='/api')
    return app


from . import models

