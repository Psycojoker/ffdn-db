#!/usr/bin/env python2
import os; os.environ['FFDNISPDB_SETTINGS'] = '../settings_dev.py'
import gevent.pywsgi
from gevent import monkey; monkey.patch_all()
import werkzeug.serving
from werkzeug.debug import DebuggedApplication
from ffdnispdb import create_app


app=create_app()

@werkzeug.serving.run_with_reloader
def runServer():
    ws = gevent.pywsgi.WSGIServer(('', 5000), DebuggedApplication(app, evalex=True))
    ws.serve_forever()

