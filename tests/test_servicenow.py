#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# -*- coding: utf-8 -*-

import os
import sys
import unittest
import mock

if sys.version_info >= (3, 0):
    import urllib.request
    import urllib.parse
    import http.client
    import urllib.error
else:
    import httplib  # noqa
    import urllib2  # noqa
    import urllib  # noqa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import servicenow  # noqa


class TestCaseServicenow(unittest.TestCase):
    def setUp(self):
        if sys.version_info >= (3, 0):
            self.urllib_name = "urllib.request"
            self.urllib_error = urllib.error
            self.bad_status = http.client.BadStatusLine
        else:
            self.urllib_name = "urllib2"
            self.urllib_error = urllib2
            self.bad_status = httplib.BadStatusLine

    def test_list_tables(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = (
            '{"result":[{"name": "sys_dictionary"}, {"name": "sc_task"}]}')
        url = "http://host:port/path"
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(url, "user", "pass")
            self.assertEqual(
                snow.tables(),
                ["sys_dictionary", "sc_task"])

    def test_get_status_ok(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = (
            '{"result":{"tasks": [{"id": 123}]}}')
        url = "http://host:port/path"
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(url, "user", "pass")
            self.assertEqual(
                snow.get("api/now/table/sc_task"),
                {"tasks": [{"id": 123}]})

    def test_get_no_msg(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = ''
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertIsNone(snow.get("api/now/table/sc_task"))

    def test_get_wrong_status(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 201
        m.return_value.msg = 'Created'
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(
                snow.get("api/now/table/sc_task"),
                {'error': {'code': 201, 'message': 'Created'}})

    def test_get_wrong_json(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = 'Returned text'
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass", proxy="toto")
            with self.assertRaises(servicenow.ServiceNowDecodeError) as e:
                snow.get("api/now/table/sc_task")
            self.assertIn(str(e.exception), ('No JSON object could be decoded', 'Expecting value: line 1 column 1 (char 0)'))

    def test_get_error_bad_status_line(self):
        m = mock.Mock()
        m.side_effect = self.bad_status(240)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass", verify=False)
            with self.assertRaises(servicenow.ServiceNowHttpError) as e:
                snow.get("api/now/table/sc_task")
            self.assertEqual(str(e.exception), 'HTTP Error -1: 240, http://host:port/path/api/now/table/sc_task')

    def test_get_error_urlerror(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'URLError')('Not connected')
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass", verify=False)
            with self.assertRaises(servicenow.ServiceNowHttpError) as e:
                snow.get("api/now/table/sc_task")
            self.assertEqual(str(e.exception), 'HTTP Error -1: Not connected, http://host:port/path/api/now/table/sc_task')

    def test_get_error_403(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            'http://', 403, 'Forbidden', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass", verify=False)
            with self.assertRaises(servicenow.ServiceNowHttpError) as e:
                snow.get("api/now/table/sc_task")
            self.assertEqual(str(e.exception), 'HTTP Error 403: Forbidden, http://host:port/path/api/now/table/sc_task')

    def test_get_error_404(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 404, 'Not Found', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.get("api/now/table/sc_task")

    def test_get_error_500(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 500, 'Internal Server Error', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.get("api/now/table/sc_task")

    def test_get_error_505(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 505, 'HTTP Version not supported', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.get("api/now/table/sc_task")

    def test_put_status_ok(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = (
            '{"result":{"message": "success"}}')
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(snow.put(
                "api/now/table/sc_task/1", {"status": "start"}
            ), {"message": "success"})

    def test_put_no_msg(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 204
        m.return_value.read.return_value = ''
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertIsNone(snow.put(
                "api/now/table/sc_task/1", {"status": "start"}
            ))

    def test_put_wrong_status(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 201
        m.return_value.msg = 'Created'
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(snow.put(
                "api/now/table/sc_task/1", {"status": "start"}
            ), {'error': {'code': 201, 'message': 'Created'}})

    def test_put_wrong_json(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = 'Returned text'
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowDecodeError):
                snow.put("api/now/table/sc_task/1", {"status": "start"})

    def test_put_error_403(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 403, 'Forbidden', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.put("api/now/table/sc_task/1", {"status": "start"})

    def test_put_error_404(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 404, 'Not Found', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.put("api/now/table/sc_task/1", {"status": "start"})

    def test_put_error_500(self):
        m = mock.Mock()
        # m.side_effect = compat_urllib.ServiceNowHttpError('', 500,
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            "", 500, 'Internal Server Error', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.put("api/now/table/sc_task/1", {"status": "start"})

    def test_put_error_505(self):
        m = mock.Mock()
        # m.side_effect = compat_urllib.ServiceNowHttpError(
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 505, 'HTTP Version not supported', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.put("api/now/table/sc_task/1", {"status": "start"})

    def test_post_status_ok(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 201
        m.return_value.read.return_value = (
            '{"result":{"success": "true"}}')
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(snow.post(
                "api/now/table/sc_task", {"task": {"id": 1}}
            ), {"success": "true"})

    def test_post_no_msg(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 204
        m.return_value.read.return_value = ''
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertIsNone(snow.post(
                "api/now/table/sc_task", {"task": {"id": 1}}
            ))

    def test_post_wrong_status(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.msg = 'OK'
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(snow.post(
                "api/now/table/sc_task", {"task": {"id": 1}}
            ), {'error': {'code': 200, 'message': 'OK'}})

    def test_post_wrong_json(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 201
        m.return_value.read.return_value = 'Returned text'
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowDecodeError):
                snow.post("api/now/table/sc_task", {"task": {"id": 1}})

    def test_post_error_403(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 403, 'Forbidden', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.post("api/now/table/sc_task", {"task": {"id": 1}})

    def test_post_error_404(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 404, 'Not Found', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.post("api/now/table/sc_task", {"task": {"id": 1}})

    def test_post_error_500(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 500, 'Internal Server Error', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.post("api/now/table/sc_task", {"task": {"id": 1}})

    def test_post_error_505(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 505, 'HTTP Version not supported', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.post("api/now/table/sc_task", {"task": {"id": 1}})

    def test_delete_status_ok(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = (
            '{"result":{"success": "true"}}')
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(
                snow.delete("api/now/table/sc_task/1"),
                {"success": "true"})

    def test_delete_no_msg(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 204
        m.return_value.read.return_value = ''
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertIsNone(snow.delete("api/now/table/sc_task/1"))

    def test_delete_wrong_status(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 207
        m.return_value.msg = 'Multi-Status'
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(
                snow.delete("api/now/table/sc_task/1"),
                {'error': {'code': 207, 'message': 'Multi-Status'}})

    def test_delete_wrong_json(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = 'Returned text'
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowDecodeError):
                snow.delete("api/now/table/sc_task/1")

    def test_delete_error_403(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 403, 'Forbidden', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.delete("api/now/table/sc_task/1")

    def test_delete_error_404(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 404, 'Not Found', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.delete("api/now/table/sc_task/1")

    def test_delete_error_500(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 500, 'Internal Server Error', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.delete("api/now/table/sc_task/1")

    def test_delete_error_505(self):
        m = mock.Mock()
        m.side_effect = getattr(self.urllib_error, 'HTTPError')(
            '', 505, 'HTTP Version not supported', None, None)
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowHttpError):
                snow.delete("api/now/table/sc_task/1")

    def test_display_field(self):
        def fake_open(request):
            mock_req = mock.Mock()
            mock_req.getcode.return_value = 200
            if 'sys_db_object' in request.get_full_url():
                if 'name%3D' in request.get_full_url():
                    mock_req.read.return_value = '[{"super_class":"123"}]'
                else:
                    mock_req.read.return_value = '[{"name":"cmdb"}]'
            if 'sys_dictionary' in request.get_full_url():
                if 'name%3Dcmdb' in request.get_full_url():
                    mock_req.read.return_value = '[{"element":"name"}]'
                else:
                    mock_req.read.return_value = '[]'
            return mock_req

        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch(
                self.urllib_name + '.OpenerDirector', m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(snow._display_field('toto'), 'name')

    def test_display_field_wo_heritance_error(self):
        def fake_open(request):
            mock_req = mock.Mock()
            mock_req.getcode.return_value = 200
            if 'sys_db_object' in request.get_full_url():
                mock_req.read.return_value = '[{"super_class":""}]'
            if 'sys_dictionary' in request.get_full_url():
                mock_req.read.return_value = '[]'
            return mock_req

        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch(
                self.urllib_name + '.OpenerDirector', m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(KeyError):
                snow._display_field('toto')

    def test_display_field_wo_heritance(self):
        def fake_open(request):
            mock_req = mock.Mock()
            mock_req.getcode.return_value = 200
            if 'sys_db_object' in request.get_full_url():
                mock_req.read.return_value = '[{"super_class":""}]'
            if 'sys_dictionary' in request.get_full_url():
                if 'display%3Dtrue' in request.get_full_url():
                    mock_req.read.return_value = '[]'
                else:
                    mock_req.read.return_value = '[{"element": "name"}]'
            return mock_req

        m = mock.Mock()
        m.return_value.open.side_effect = fake_open
        with mock.patch(
                self.urllib_name + '.OpenerDirector', m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(snow._display_field('toto'), 'name')

    def test_sysid_to_value_no_heritance(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = '[{"super_class":""}]'
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowReferenceNotFound) as e:
                snow.sysid_to_value("table", "123")
            self.assertEqual(str(e.exception), '123 in table')

    def test_sysid_to_value(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.side_effect = ['[{"element": "name"}]', '{"result":{"name": "toto"}}']
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(snow.sysid_to_value("table", "123"), 'toto')

    def test_sysid_to_value_not_found(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.side_effect = ['[{"element": "name"}]', '{"result":{}}']
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowReferenceNotFound):
                snow.sysid_to_value("table", "123")

    def test_value_to_sysid(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.side_effect = ['[{"element": "name"}]', '{"result":[{"sys_id": "123"}]}']
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            self.assertEqual(snow.value_to_sysid("table", "value"), '123')

    def test_value_to_sysid_not_found(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.side_effect = ['[{"element": "name"}]', '{"result":[]}']
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowReferenceNotFound) as e:
                snow.value_to_sysid("table", "value")
            self.assertEqual(str(e.exception), 'value in table')

    def test_value_to_sysid_no_heritance(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = '[{"super_class": ""}]'
        with mock.patch(
                self.urllib_name + ".OpenerDirector.open", m, create=True):
            snow = servicenow.ServiceNow(
                "http://host:port/path", "user", "pass")
            with self.assertRaises(servicenow.ServiceNowReferenceNotFound):
                snow.value_to_sysid("table", "value")


if __name__ == '__main__':
    import logging
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
