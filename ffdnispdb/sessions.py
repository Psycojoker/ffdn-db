

from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict

from sqlalchemy import Table, Column, String, LargeBinary, DateTime,\
                       select, delete, insert, update

from random import SystemRandom, randrange
import string
from datetime import datetime, timedelta
import cPickle

random=SystemRandom()


class SQLSession(CallbackDict, SessionMixin):

    def __init__(self, sid, db, table, new=False, initial=None):
        self.sid=sid
        self.db=db
        self.table=table
        self.modified=False
        self.new=new
        def _on_update(self):
            self.modified=True
        super(SQLSession, self).__init__(initial, _on_update)

    def save(self):
        if self.new:
            self.db.execute(self.table.insert({
                'session_id': self.sid,
                'expire': datetime.now()+timedelta(hours=1),
                'value': cPickle.dumps(dict(self), -1)
            }))
            self.new=False
        else:
            self.db.execute(self.table.update(
                self.table.c.session_id == self.sid,
                {
                    'expire': datetime.now()+timedelta(hours=1),
                    'value': cPickle.dumps(dict(self), -1)
                }
            ))


class MySessionInterface(SessionInterface):
    def __init__(self, db):
        self.db = db

        self.table = Table('flask_sessions', db.metadata,
            Column('session_id', String(32), primary_key=True),
            Column('expire', DateTime, index=True),
            Column('value', LargeBinary, nullable=False)
        )

    def open_session(self, app, request):
        sid = request.cookies.get(app.session_cookie_name)
        if sid:
            res=self.db.engine.execute(select([self.table.c.value], (self.table.c.session_id == sid) &
                                                                 (self.table.c.expire > datetime.now()))).first()
            if res:
                return SQLSession(sid, self.db.engine, self.table, False, cPickle.loads(res[0]))

        while True:
            sid=''.join(random.choice(string.ascii_letters+string.digits) for i in range(32))
            res=self.db.engine.execute(select([self.table.c.value], self.table.c.session_id == sid)).first()
            if not res:
                break

        return SQLSession(sid, self.db.engine, self.table, True)

    def save_session(self, app, session, response):
        if session.modified:
            session.save()

        # remove expired sessions.. or maybe not
        if randrange(20) % 20 == 0:
            self.db.engine.execute(self.table.delete(self.table.c.expire <= datetime.now()))

        response.set_cookie(app.session_cookie_name, session.sid,
                            expires=self.get_expiration_time(app, session),
                            domain=self.get_cookie_domain(app),
                            path=self.get_cookie_path(app),
                            secure=self.get_cookie_secure(app),
                            httponly=self.get_cookie_httponly(app))
