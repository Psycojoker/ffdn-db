import gevent.pywsgi
from gevent import monkey; monkey.patch_all()
import werkzeug.serving
from werkzeug.debug import DebuggedApplication
from ffdnispdb import app


@werkzeug.serving.run_with_reloader
def runServer():
    app.debug = True
    ws = gevent.pywsgi.WSGIServer(('', 5000), DebuggedApplication(app, evalex=True))
    ws.serve_forever()

