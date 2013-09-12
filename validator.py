#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
from ffdnispdb.schemavalidator import validate_isp

if len(sys.argv) == 2:
    j=json.load(open(sys.argv[1]))
    errs=list(validate_isp(j))
    if errs:
        for e in errs:
            print e
    else:
        print "All clear"
else:
    print "Usage: validator.py file-name.json"

