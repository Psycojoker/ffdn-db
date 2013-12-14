#!/usr/bin/env python2

# MyServer
import gevent.pywsgi
from gevent import monkey; monkey.patch_all()
import werkzeug.serving
from werkzeug.debug import DebuggedApplication

import os; os.environ.setdefault('FFDNISPDB_SETTINGS', '../settings_dev.py')
from flask.ext.script import (Shell, Server, Manager, Command, Option,
                              prompt, prompt_bool, prompt_pass)
import ffdnispdb



database_manager = Manager(usage=u'Perform database operations')

@database_manager.command
def create():
    "Initialize database, create tables"
    ffdnispdb.db.create_all()


@database_manager.command
def drop():
    "Drop existing tables"
    if prompt_bool("Are you sure you wish to destroy existing database"):
        ffdnispdb.db.drop_all()


index_manager = Manager(usage=u'Manage the Whoosh index')

@index_manager.command
def rebuild():
    "Rebuild the Whoosh index from SQL datatabase"
    from ffdnispdb.models import ISP, ISPWhoosh
    from whoosh import writing
    import shutil

    shutil.rmtree(ISPWhoosh.get_index_dir())
    idx=ISPWhoosh.get_index()
    with idx.writer() as writer:
        for isp in ISP.query.all():
            ISPWhoosh.update_document(writer, isp)

        writer.mergetype = writing.CLEAR
        writer.optimize = True


class MyServer(Server):
    def handle(self, app, host, port, use_debugger, use_reloader,
               threaded, processes, passthrough_errors):
        if use_debugger:
            app=DebuggedApplication(app, evalex=True)

        @werkzeug.serving.run_with_reloader
        def run():
            ws = gevent.pywsgi.WSGIServer(('', 5000), app)
            ws.serve_forever()


def shell_context():
    import ffdnispdb
    return ffdnispdb.__dict__


class RunTests(Command):
    "Run unit-tests"
    option_list = (
        Option('--verbose', '-v', action='store_true', default=False),
        Option('--failfast', '-f', action='store_true', default=False),
    )

    def run(self, verbose, failfast):
        import unittest
        import test_ffdnispdb
        test=unittest.defaultTestLoader.loadTestsFromModule(test_ffdnispdb)
        unittest.TextTestRunner(verbosity=2 if verbose else 1, failfast=bool(failfast)).run(test)


manager = Manager(ffdnispdb.create_app)
manager.add_command("runserver", MyServer())
manager.add_command("shell", Shell(make_context=shell_context))
manager.add_command("db", database_manager)
manager.add_command("index", index_manager)
manager.add_command("test", RunTests())

if __name__ == "__main__":
    manager.run()
