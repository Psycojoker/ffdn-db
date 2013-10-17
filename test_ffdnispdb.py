
from ffdnispdb import app, db
from ffdnispdb.models import ISP
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import unittest
import os


class TestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        # Ugly, but should work in this context... ?
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.drop_all()

    def test_projectform(self):
        resp = self.app.post('/create/form', data={
            'name': 'Test',
            'step': '1',
            'covered_areas-0-name': 'Somewhere over the rainbow',
            'covered_areas-0-technologies': 'dsl',
            'covered_areas-0-technologies': 'ftth'
        })
        self.assertNotEqual(resp.location, None)
        self.assertEqual(ISP.query.filter_by(name='Test').count(), 1)


if __name__ == '__main__':
    unittest.main()
