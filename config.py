# -*- coding: utf-8 -*-

SQLALCHEMY_DATABASE_URI = 'sqlite:///../ffdn-db.sqlite'
#PASSWD_SALT = 'change this value to some random chars!'
SECRET_KEY = '{J@uRKO,xO-PK7B,jF?>iHbxLasF9s#zjOoy=+:'
DEBUG = True
CRAWLER_MIN_CACHE_TIME=60*60 # 1 hour
CRAWLER_MAX_CACHE_TIME=60*60*24*14 # 2 week
CRAWLER_DEFAULT_CACHE_TIME=60*60*12 # 12 hours
EMAIL_SENDER='FFDN DB <no-reply@db.ffdn.org>'
#MAIL_SERVER=''
#SERVER_NAME = 'db.ffdn.org'
