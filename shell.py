#!/usr/bin/env python2
import os; os.environ['FFDNISPDB_SETTINGS'] = '../settings_dev.py'
import os
import readline
from pprint import pprint

from flask import *
from ffdnispdb import *

app=create_app()

app.app_context().push()
os.environ['PYTHONINSPECT'] = 'True'
