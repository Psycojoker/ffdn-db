#!/usr/bin/env python2
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
