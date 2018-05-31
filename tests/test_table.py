#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# -*- coding: utf-8 -*-

import os
import sys
import unittest
import mock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from servicenow.table import ServiceNow  # noqa


class TestCaseServicenowTable(unittest.TestCase):

    def test_len(self):
        def fake_open(request):
            params = request.get_full_url().split('?')[1].split('&')
            (limit, offset) = (1, 1)
            mock_req = mock.Mock()
            mock_req.getcode.return_value = 200
            for p in params:
                if p.startswith('sysparm_limit'):
                    limit = int(p.split('=')[1])
                if p.startswith('sysparm_offset'):
                    offset = int(p.split('=')[1])
            tab = range(1, 10)
            mock_req.read.return_value = str(tab[offset:limit + offset])
            return mock_req
        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch('urllib2.OpenerDirector', m, create=True):
            snow = ServiceNow("url", "user", "pass")
            self.assertEquals(len(snow.Table('toto')), 9)

    def test_getitem(self):
        def fake_open(request):
            params = request.get_full_url().split('?')[1].split('&')
            (limit, offset) = (1, 1)
            mock_req = mock.Mock()
            mock_req.getcode.return_value = 200
            for p in params:
                if p.startswith('sysparm_limit'):
                    limit = int(p.split('=')[1])
                if p.startswith('sysparm_offset'):
                    offset = int(p.split('=')[1])
            tab = [{'name': 'uh'+str(i)} for i in range(1, 10)]
            mock_req.read.return_value = \
                str(tab[offset:limit + offset]).replace("'", "\"")
            return mock_req
        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch('urllib2.OpenerDirector', m, create=True):
            snow = ServiceNow("url", "user", "pass")
            first = snow.Table('toto')[3]
            self.assertEquals(first['name'], 'uh4')
            self.assertEquals(first.name, 'uh4')

    def test_search(self):
        def fake_open(request):
            params = request.get_full_url().split('?')[1].split('&')
            for p in params:
                if p.startswith('sysparm_query'):
                    retval = []
                    for s in p.split('=', 1)[1].split("^"):
                        retval.append({'data': s})
                    retval = str(retval).replace("'", "\"")
                    break
            else:
                retval = '[{"name":"test","toto":"tataouine"}]'
            mock_req = mock.Mock()
            mock_req.getcode.return_value = 200
            mock_req.read.return_value = retval
            return mock_req
        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch('urllib2.OpenerDirector', m, create=True):
            snow = ServiceNow("url", "user", "pass")
            for i in snow.Table('toto').search('name=toto', 'totoLIKEtata'):
                self.assertIn("data", i)
                self.assertIn(i['data'], ['name=toto', 'totoLIKEtata'])

    def test_search_wrong_field(self):
        def fake_open(request):
            mock_req = mock.Mock()
            mock_req.getcode.return_value = 200
            mock_req.read.return_value = \
                '[{"name":"test", "toto":"tataouine"}]'
            return mock_req
        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch('urllib2.OpenerDirector', m, create=True):
            snow = ServiceNow("url", "user", "pass")
            with self.assertRaises(KeyError):
                for i in snow.Table('toto').search('wrong=field'):
                    pass
