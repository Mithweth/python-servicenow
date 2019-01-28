#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# -*- coding: utf-8 -*-
import json
import logging
import os
import sys
import unittest
import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import servicenow.table # noqa


class FakePaginate: 
    def __init__(self, data_list):
        self.__data_list = data_list
        self.url_params_list = []

    def fake_open(self, request):
        params = request.get_full_url().split('?')[1].split('&')
        limit = None
        tmp = {}
        for p in params:
            if p == "":
                continue
            name, value = p.split('=')
            if name in ('sysparm_limit', 'sysparm_offset', 'sysparm_display_value'):
                tmp[name] = value
            else:
                raise Exception("unexpected param:%s in url:%s" % (
                    p, request.get_full_url()))
        if tmp["sysparm_limit"] == None:
            raise Exception("no sysparm_limit found in url:%s" % request.get_full_url())
        retval = []
        for i in range(0, int(tmp["sysparm_limit"])):
            try:
                retval.append(self.__data_list.pop())
            except IndexError:
                pass
        tmp["result.len"] = len(retval)
        tmp["retval"] = retval
        self.url_params_list.append(tmp)
        mock_req = mock.Mock()
        if len(retval) == 0:
            mock_req.getcode.return_value = 404
            mock_req.read.return_value = ""
        else:
            mock_req.getcode.return_value = 200
            mock_req.read.return_value = json.dumps(retval)
        return mock_req


class TestCaseServicenowTable(unittest.TestCase):
    def setUp(self):
        if sys.version_info >= (3, 0):
            self.urllib_name = "urllib.request"
            self.compat_urllib = __import__(
                "urllib.request", fromlist=("request",))
        else:
            self.urllib_name = "urllib2"
            self.compat_urllib = __import__("urllib2")
        try:
            v_loglevel = os.environ["LOGLEVEL"]
        except KeyError:
            v_loglevel = "WARN"
        self.__logger = logging.getLogger("servicenow")
        self.__logger.setLevel(getattr(logging, v_loglevel))
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)-s "
            "%(filename)s:%(funcName)s:%(lineno)d %(message)s")

        if len(self.__logger.handlers) == 0:
            handler_console = logging.StreamHandler()
            handler_console.setFormatter(formatter)
            handler_console.setLevel(getattr(logging, v_loglevel))
            self.__logger.addHandler(handler_console)

    def test_sysid_to_value(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.side_effect = ['[{"element": "name"}]', '{"result":{"name": "toto"}}']
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.table.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(snow.sysid_to_value("table", "123"), 'toto')
            self.assertIn('table.123', snow._cache)
            self.assertEqual(snow._cache['table.123'], 'toto')

    def test_sysid_to_value_with_cache(self):
        m = mock.Mock()
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.table.ServiceNow(
                "http://host:port/path", "user", "pass")
            snow._cache['table.123'] = 'toto'
            self.assertEqual(snow.sysid_to_value("table", "123"), 'toto')
            self.assertEqual(len(m.mock_calls), 0)

    def test_value_to_sysid(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.side_effect = ['[{"element": "name"}]', '{"result":[{"sys_id": "123"}]}']
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.table.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(snow.value_to_sysid("table", "value"), '123')
            self.assertIn('table.value', snow._cache)
            self.assertEqual(snow._cache['table.value'], '123')

    def test_value_to_sysid_with_cache(self):
        m = mock.Mock()
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.table.ServiceNow(
                "http://host:port/path", "user", "pass")
            snow._cache['table.value'] = '123'
            self.assertEqual(snow.value_to_sysid("table", "value"), '123')
            self.assertEqual(len(m.mock_calls), 0)

    def test_repr(self):
        snow = servicenow.table.ServiceNow(
            "http://host:port/path", "user", "pass")
        table = snow.Table('toto')
        self.assertEqual(repr(table), 'Table(toto)')

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
            tab = range(1, 75000)
            mock_req.read.return_value = str(list(tab[offset:limit + offset]))
            return mock_req
        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch(
                self.urllib_name + ".OpenerDirector", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            self.assertEqual(len(snow.Table('toto')), 74999)

    def test_empty_length(self):
        def fake_open(request):
            m = mock.Mock()
            m.getcode.return_value = 200
            m.read.return_value = '{"result":[]}'
            return m
        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch(
                self.urllib_name + ".OpenerDirector", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            self.assertEqual(len(snow.Table('toto')), 0)

    def test_delitem(self):
        m = mock.Mock()
        m.return_value = [{"sys_id":"123", "name":"toto"}]
        with mock.patch(
                "servicenow.ServiceNow._call", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = snow.Table('toto')
            del table[2]
        m.assert_called_with('DELETE', 'http://h:1/api/now/table/toto/123', status_codes=(200, 202, 204))

    def test_remove(self):
        m = mock.Mock()
        m.return_value = [{"sys_id":"123", "name":"toto"}]
        with mock.patch(
                "servicenow.ServiceNow._call", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = snow.Table('toto')
            table.remove('123')
        m.assert_called_with('DELETE', 'http://h:1/api/now/table/toto/123', status_codes=(200, 202, 204))

    def test_insert(self):
        m = mock.Mock()
        m.return_value = [{"sys_id":"123", "name":"toto"}]
        with mock.patch(
                "servicenow.ServiceNow._call", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = snow.Table('toto')
            table.insert({'name':'toto', 'sys_id': '456'})
        m.assert_called_with('POST', 'http://h:1/api/now/table/toto', status_codes=(201, 204), params={'name': u'toto'})

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
        with mock.patch(
                self.urllib_name + ".OpenerDirector", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            first = snow.Table('toto')[3]
            self.assertEqual(first['name'], 'uh4')
            self.assertEqual(first.name, 'uh4')

    def test_no_item(self):
        def fake_open(request):
            mock_req = mock.Mock()
            mock_req.getcode.return_value = 200
            mock_req.read.return_value = '{"result":[]}'
            return mock_req
        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch(
                self.urllib_name + ".OpenerDirector", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = snow.Table('toto')
            self.assertIsNone(table[0])
            self.assertIsNone(table[3])

    def test_negative_item(self):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = snow.Table('toto')
            self.assertIsNone(table[-1])

    def test_prepare_no_filters(self):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = snow.Table('toto')
            with self.assertRaises(Exception):
                table._prepare()

    def test_prepare_no_usable_filters(self):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = snow.Table('toto')
            with self.assertRaises(Exception):
                table._prepare('')

    def test_prepare_not_implemented(self):
        snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
        table = snow.Table('toto')
        with self.assertRaises(NotImplementedError):
            table._prepare('keyEQUALSvalue')

    def test_prepare_with_link(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.side_effect = [
            '[{"env": {"link": "new_table/123","value":"123"}}]',
            '[{"element": "name"}]',
            '[{"env"}]']
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = snow.Table('toto')
            self.assertEqual(table._prepare('', 'env=value'), 'env=value^ORenv.name=value')

    def test_prepare_with_empty_link(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.side_effect = [
            '[{"env": {"value":"123"}}]',
            '[{"value": "1"}]',
            '[{"value": "1"}]']
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = snow.Table('toto')
            self.assertEqual(table._prepare('env=value'), 'env=value')

    def test_filter_query(self):
        def fake_open(request):
            params = request.get_full_url().split('?')[1].split('&')
            mock_req = mock.Mock()
            mock_req.getcode.return_value = 200
            data = [{i.split('=')[0]: i.split('=')[1] for i in params} for h in range(0,30)]
            mock_req.read.return_value = json.dumps(data)
            return mock_req
        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch(
                self.urllib_name + ".OpenerDirector", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            j = 0
            for i in snow.Table('toto').filter(query='nameLIKEbt1', fields='name', order='name', limit=5):
                j += 1
            self.assertEqual(j, 5)
            self.assertIn('sysparm_fields', i)
            self.assertEqual(i['sysparm_fields'], 'name')
            self.assertIn('sysparm_query', i)
            self.assertEqual(i['sysparm_query'], 'nameLIKEbt1%5EORDERBYname')

    def test_search_paginate_default_00(self):
        data_list = []
        for i in range(0, 352):
            data_list.append({
                "a": i * 10
            })
        m = mock.Mock()
        f = FakePaginate(list(data_list))
        m.return_value.open.side_effect = f.fake_open
        with mock.patch(
                self.urllib_name + ".OpenerDirector", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = servicenow.table.Table(snow, 'toto')
            c = 0
            for i in table:
                c += 1
            self.assertEqual(len(data_list), c)

    def test_search_paginate_default_adaptative(self):
        data_list = []
        for i in range(0, 355):
            data_list.append({
                "a": i * 10
            })
        m = mock.Mock()
        f = FakePaginate(list(data_list))
        m.return_value.open.side_effect = f.fake_open
        with mock.patch(
                self.urllib_name + ".OpenerDirector", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = servicenow.table.Table(snow, 'toto')
            c = 0
            for i in table:
                c += 1
            self.assertEqual(len(data_list), c)
        self.assertEqual(f.url_params_list[0]["sysparm_offset"], "0")
        self.assertEqual(f.url_params_list[0]["result.len"], 30)

        self.assertEqual(f.url_params_list[1]["sysparm_offset"], "30")
        self.assertGreater(int(f.url_params_list[1]["sysparm_limit"]), 30)
        self.assertGreater(f.url_params_list[1]["result.len"], 30)

    def test_search_paginate_2_5(self):
        data_list = []
        for i in range(0, 355):
            data_list.append({
                "a": i * 10
            })
        m = mock.Mock()
        f = FakePaginate(list(data_list))
        m.return_value.open.side_effect = f.fake_open
        with mock.patch(
                self.urllib_name + ".OpenerDirector", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = servicenow.table.Table(snow, 'toto')
            c = 0
            for i in table.search():
                c += 1
            self.assertEqual(len(data_list), c)
        self.assertEqual(f.url_params_list[0]["sysparm_offset"], "0")
        self.assertEqual(f.url_params_list[0]["result.len"], 50)

        self.assertEqual(f.url_params_list[1]["sysparm_offset"], "50")
        self.assertEqual(f.url_params_list[1]["sysparm_limit"], "50")
        self.assertEqual(f.url_params_list[1]["result.len"], 50)

        self.assertEqual(f.url_params_list[2]["sysparm_offset"], "100")
        self.assertEqual(f.url_params_list[2]["sysparm_limit"], "50")
        self.assertEqual(f.url_params_list[2]["result.len"], 50)


    def test_search_paginate_2_5(self):
        data_list = []
        for i in range(0, 5):
            data_list.append({
                "a": i * 10
            })
        m = mock.Mock()
        f = FakePaginate(list(data_list))
        m.return_value.open.side_effect = f.fake_open
        with mock.patch(
                self.urllib_name + ".OpenerDirector", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = servicenow.table.TableIterator(snow, 'toto')
            table._default_pagesize = 2
            c = 0
            for i in table:
                c += 1
            self.assertEqual(len(data_list), c)
        # 5 entree dans la liste, il faut 3 requetes de limit=2
        self.assertEqual(f.url_params_list[0]["sysparm_offset"], "0")
        self.assertEqual(f.url_params_list[0]["sysparm_limit"], "2")
        self.assertEqual(f.url_params_list[0]["result.len"], 2)

        self.assertEqual(f.url_params_list[1]["sysparm_offset"], "2")
        self.assertEqual(f.url_params_list[1]["result.len"], 3)

        self.assertEqual(len(f.url_params_list), 2)

    def test_search_paginate_3_8(self):
        data_list = []
        for i in range(0, 8):
            data_list.append({
                "a": i * 11
            })
        m = mock.Mock()
        f = FakePaginate(list(data_list))
        m.return_value.open.side_effect = f.fake_open
        with mock.patch(
                self.urllib_name + ".OpenerDirector", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            table = servicenow.table.TableIterator(snow, 'toto')
            table._default_pagesize = 3
            c = 0
            for i in table:
                c += 1
            self.assertEqual(len(data_list), c)
        # 8 entree dans la liste, il faut 3 requetes de limit=3
        self.assertEqual(f.url_params_list[0]["sysparm_offset"], "0")
        self.assertEqual(f.url_params_list[0]["sysparm_limit"], "3")
        self.assertEqual(f.url_params_list[0]["result.len"], 3)

        self.assertEqual(f.url_params_list[1]["sysparm_offset"], "3")
        self.assertEqual(f.url_params_list[1]["result.len"], 5)

    def test_search_wrong_field(self):
        def fake_open(request):
            mock_req = mock.Mock()
            mock_req.getcode.return_value = 200
            mock_req.read.return_value = \
                '[{"name":"test", "toto":"tataouine"}]'
            return mock_req
        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch(
                self.urllib_name + ".OpenerDirector", m, create=True):
            snow = servicenow.table.ServiceNow("http://h:1", "user", "pass")
            with self.assertRaises(KeyError):
                for i in snow.Table('toto').search('wrong=field'):
                    pass

    def test_inequality(self):
        table = servicenow.table.ServiceNow("http://h:1", "user", "pass").Table('toto')
        tr1 = servicenow.table.TableRow(table, {'name':'toto', 'adr':'ici','plop':'123'})
        tr2 = servicenow.table.TableRow(table, {'name':'toto', 'adr':'ici','data':'256'})
        tr3 = servicenow.table.TableRow(table, {'name':'toto', 'adr':'ici','sys_id':'256'})
        tr4 = servicenow.table.TableRow(table, {'name':'toto', 'adr':'la','plop':'123'})
        tr5 = servicenow.table.TableRow(table, {'name':'toto', 'adr':'ici','plop':'123', 'data':'other'})
        self.assertFalse(tr2 == tr1)
        self.assertFalse(tr1 == tr3)
        self.assertFalse(tr1 == tr4)
        self.assertFalse(tr1 == tr5)

    def test_equality(self):
        table = servicenow.table.ServiceNow("http://h:1", "user", "pass").Table('toto')
        tr1 = servicenow.table.TableRow(table, {'name':'toto', 'adr':'ici','sys_id':'123'})
        tr2 = servicenow.table.TableRow(table, {'name':'toto', 'adr':'ici','sys_id':'256'})
        self.assertTrue(tr1 == tr2)

    def test_setitem(self):
        parent = mock.MagicMock()
        parent.snow = mock.MagicMock()
        parent.table = "table0"
 
        data = {
            "sys_id": "sys_id0",
            "name0": "value_old"
        }
        row = servicenow.table.TableRow(parent, data)

        row["name0"] = "value_new"
        self.assertEqual(row["name0"], row["name0"].value)
        self.assertEqual(len(parent.snow.mock_calls), 1)
        parent.snow.put.assert_called_with(
            'table0/sys_id0', {'name0': 'value_new'}
        )

    def test_setitem_display_value(self):
        parent = mock.MagicMock()
        parent.snow = mock.MagicMock()
        parent.table = "table0"

        data = {
            "sys_id": "sys_id0",
            "name0": {"link":"http://", "display_value": "value_old"}
        }
        row = servicenow.table.TableRow(parent, data)

        row["name0"] = "value_new"
        self.assertEqual(row["name0"], row["name0"].display_value)
        self.assertEqual(len(parent.snow.mock_calls), 1)
        parent.snow.put.assert_called_with(
            'table0/sys_id0', {'name0': 'value_new'}
        )


if __name__ == '__main__':
    import logging
    v_loglevel = "DEBUG"
    v_loglevel = "WARN"
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, v_loglevel))
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-s %(funcName)s:%(lineno)d %(message)s")

    handler_console = logging.StreamHandler()
    handler_console.setFormatter(formatter)
    handler_console.setLevel(getattr(logging, v_loglevel))
    logger.addHandler(handler_console)
    unittest.main()
