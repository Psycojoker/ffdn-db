
from . import db


class ISP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, index=True, unique=True)
    shortname = db.Column(db.String(12), index=True, unique=True)
    url = db.Column(db.String)
    lastSuccessfulUpdate = db.Column(db.DateTime)
    lastUpdateAttempt = db.Column(db.DateTime)
    isUpdatable = db.Column(db.Boolean, default=True) # set to False to disable JSON updates
    techEmailContact = db.Column(db.String)
    cacheInfo = db.Column(db.Text)
    json = db.Column(db.Text)

    def __repr__(self):
        return '<ISP %r>' % self.shortname if self.shortname else self.name

        
