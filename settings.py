#!/usr/bin/env python
# -*- coding: utf-8 -*-

DATABASE = './ffdn-db.sqlite'
#PASSWD_SALT = 'change this value to some random chars!'
SECRET_KEY = '{J@uRKO,xO-PK7B,jF?>iHbxLasF9s#zjOoy=+:'
DEBUG = True
TITLE = u"Fédéral Database"
#EMAIL = '"' + TITLE + '"' + ' <' + u"cavote@ffdn.org" + '>'
#VERSION = "cavote 0.3.0"
#SMTP_SERVER = "127.0.0.1"
#PATTERNS = {u'Oui/Non': [u'Oui', u'Non'], u'Oui/Non/Blanc': [u'Oui', u'Non', u'Blanc'], u'Oui/Non/Peut-être': [u'Oui', u'Non', u'Peut-être']}
STEPS = {1:u'Projet envisagé', 2:u'Porteurs du projet identifiés', 3:u'Structure en cours de création', 4:u'Structure constituée', 5:u'Outils de base créés (compte en banque, premiers adhérents)', 6:u'FAI opérationnel partiellement (premiers accès ouverts, p-e en mode dégradé)', 7:u'FAI pleinement opérationnel'}
STEPS_LABELS = {1:'', 2:'info', 3:'info', 4:'important', 5:'important', 6:'warning', 7:'success'}
