
from ffdnispdb import create_app, db
from ffdnispdb.models import ISP
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import unittest
import doctest
import os


class TestCase(unittest.TestCase):

    def create_app(self, **kwargs):
        test_cfg={
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        }
        test_cfg.update(kwargs)
        return create_app(test_cfg)

    def setUp(self):
        self.app = self.create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
        self._ctx = self.app.test_request_context()
        self._ctx.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self._ctx.pop()

    def assertStatus(self, response, status_code):
        self.assertEqual(response.status_code, status_code)


class TestForm(TestCase):

    def test_index(self):
        self.assertStatus(self.client.get('/'), 200)
        self.assertStatus(self.client.get('/isp/map_data.json'), 200)

    def test_projectform(self):
        resp = self.client.post('/isp/create/form', data={
            'tech_email': 'admin@isp.com',
            'name': 'Test',
            'step': '1',
            'covered_areas-0-name': 'Somewhere over the rainbow',
            'covered_areas-0-technologies': 'dsl',
            'covered_areas-0-technologies': 'ftth'
        })
        self.assertNotEqual(resp.location, None)
        self.assertEqual(ISP.query.filter_by(name='Test').count(), 1)


def load_tests(loader, tests, ignore):
    from ffdnispdb import views, models, utils, forms, crawler, sessions
    tests.addTests(doctest.DocTestSuite(views))
    tests.addTests(doctest.DocTestSuite(models))
    tests.addTests(doctest.DocTestSuite(utils))
    tests.addTests(doctest.DocTestSuite(forms))
    tests.addTests(doctest.DocTestSuite(crawler))
    return tests


if __name__ == '__main__':
    unittest.main()
