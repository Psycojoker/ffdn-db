
from ffdnispdb import create_app, db, utils
from ffdnispdb.models import ISP
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import unittest
import doctest
import json



def ISP_fixtures():
    isp1, isp2 = ISP(), ISP()
    isp1.name = 'Test ISP 1'
    isp1.shortname = 'ISP1'
    isp1.json_url = 'http://doesnt.exists/isp.json'
    isp1.json = {
        'name': 'Test ISP 1',
        'shortname': 'ISP1',
        'coveredAreas': [
            {
                'name': 'Some Area',
                'technologies': ['dsl'],
                'area': { "type": "Polygon", "coordinates": [[
                    [ 0.889892578125, 48.32703913063476 ],
                    [ 0.054931640625, 47.39834920035926 ],
                    [ 0.142822265625, 46.837649560937464 ],
                    [ 2.911376953125, 46.42271253466717 ],
                    [ 4.39453125, 46.98774725646565 ],
                    [ 4.4384765625, 48.52388120259336 ],
                    [ 2.5927734375, 48.8936153614802 ],
                    [ 0.889892578125, 48.32703913063476 ]
                ]]}
            },
            {
                'name': 'Some Other Area',
                'technologies': ['ftth'],
            },
        ],
        'version': 0.1
    }
    isp2.name = 'Test ISP 2'
    isp2.shortname = 'ISP2'
    isp2.json_url = 'http://doesnt.exists/isp.json'
    isp2.json = {
        'name': 'Test ISP 2',
        'shortname': 'ISP2',
        'coveredAreas': [
            {
                'name': 'Middle of nowhere',
                'technologies': ['dsl'],
                'area': { "type": "Polygon", "coordinates": [[
                    [ 0.889892578125, 48.32703913063476 ],
                    [ 0.054931640625, 47.39834920035926 ],
                    [ 0.142822265625, 46.837649560937464 ],
                    [ 2.911376953125, 46.42271253466717 ],
                    [ 4.39453125, 46.98774725646565 ],
                    [ 4.4384765625, 48.52388120259336 ],
                    [ 2.5927734375, 48.8936153614802 ],
                    [ 0.889892578125, 48.32703913063476 ]
                ]]}
            },
            {
                'name': 'Urban Area',
                'technologies': ['ftth'],
            },
        ],
        'version': 0.1
    }
    return (isp1, isp2)



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


class TestAPI(TestCase):
    def setUp(self):
        super(TestAPI, self).setUp()
        db.session.add_all(ISP_fixtures())
        db.session.commit()

    def check_isp_apiobj(self, isp, apiobj):
        self.assertEqual(apiobj['is_ffdn_member'], isp.is_ffdn_member)
        self.assertEqual(apiobj['json_url'], isp.json_url)
        self.assertEqual(apiobj['date_added'], utils.tosystemtz(isp.date_added).isoformat())
        self.assertEqual(apiobj['last_update'],
                         utils.tosystemtz(isp.last_update_success).isoformat()
                                if isp.last_update_success else None)
        self.assertEqual(apiobj['ispformat'], isp.json)

    def check_coveredarea_apiobj(self, ca, apiobj):
        self.assertEqual(apiobj['name'], ca.name)
        self.assertEqual(apiobj['geojson'], json.loads(ca.area_geojson)
                                if ca.area_geojson is not None else None)

    def test_isps(self):
        c = self.client.get('/api/v1/isp/')
        self.assertStatus(c, 200)
        resp = json.loads(c.data)
        isps = ISP.query.filter_by(is_disabled=False)
        self.assertEqual(isps.count(),
                         resp['total_items'])

        for isp in isps:
            m = filter(lambda i: i['id'] == isp.id, resp['isps'])[0]
            self.check_isp_apiobj(isp, m)


    def test_isp(self):
        isps = ISP.query.filter_by(is_disabled=False).all()
        victim = isps[0]
        c = self.client.get('/api/v1/isp/%d/'%victim.id)
        self.assertStatus(c, 200)
        resp = json.loads(c.data)
        self.check_isp_apiobj(victim, resp)

        victim.is_disabled = True
        db.session.commit()
        c = self.client.get('/api/v1/isp/%d/'%victim.id)
        self.assertStatus(c, 404)

        victim = isps[1]
        c = self.client.get('/api/v1/isp/%d/covered_areas/'%victim.id)
        resp = json.loads(c.data)
        for ca in victim.covered_areas:
            m = filter(lambda i: i['id'] == ca.id, resp['covered_areas'])[0]
            self.check_coveredarea_apiobj(ca, m)


    def test_urls(self):
        db_urls = ISP.query.filter(ISP.json_url != None).values('json_url')
        db_urls = [u[0] for u in db_urls]
        c = self.client.get('/api/v1/isp/export_urls/')
        self.assertStatus(c, 200)
        api_urls = map(lambda x: x['json_url'], json.loads(c.data)['isps'])
        self.assertEqual(len(api_urls), len(db_urls))
        for au in api_urls:
            self.assertIn(au, db_urls)



    def test_coveredarea(self):
        isp = ISP.query.filter_by(is_disabled=False).first()
        c = self.client.get('/api/v1/isp/%d/covered_areas/'%isp.id)
        self.assertStatus(c, 200)
        resp = json.loads(c.data)
        for ca in isp.covered_areas:
            m = filter(lambda i: i['id'] == ca.id, resp['covered_areas'])[0]
            self.check_coveredarea_apiobj(ca, m)



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
