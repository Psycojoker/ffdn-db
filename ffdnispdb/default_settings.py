# -*- coding: utf-8 -*-

SQLALCHEMY_DATABASE_URI = 'sqlite:///../ffdn-db.sqlite'
CRAWLER_MIN_CACHE_TIME = 60*60 # 1 hour
CRAWLER_MAX_CACHE_TIME = 60*60*24*14 # 2 week
CRAWLER_DEFAULT_CACHE_TIME = 60*60*12 # 12 hours
SYSTEM_TIME_ZONE='Europe/Paris'
LANGUAGES = {
    'en': 'English',
    'fr': 'Français',
}
