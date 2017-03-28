#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# -*- coding: utf-8 -*-

import os
import sys
import unittest
import mock
import urllib2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import servicenow # noqa


class TestCaseServicenow(unittest.TestCase):

    def test_get_status_ok(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = (
            '{"result":{"tasks": [{"id": 123}]}}')
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertEqual(
                snow.get("api/now/table/sc_task"),
                {"tasks": [{"id": 123}]})

    def test_get_no_msg(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = ''
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertIsNone(snow.get("api/now/table/sc_task"))

    def test_get_wrong_status(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 201
        m.return_value.msg = 'Created'
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertEqual(
                snow.get("api/now/table/sc_task"),
                {'error': {'code': 201, 'message': 'Created'}})

    def test_get_wrong_json(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = 'Returned text'
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.DecodeError):
                snow.get("api/now/table/sc_task")

    def test_get_error_403(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 403, 'Forbidden', None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.get("api/now/table/sc_task")

    def test_get_error_404(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 404, 'Not Found', None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.get("api/now/table/sc_task")

    def test_get_error_500(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 500,
                                          'Internal Server Error',
                                          None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.get("api/now/table/sc_task")

    def test_get_error_505(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 505,
                                          'HTTP Version not supported',
                                          None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.get("api/now/table/sc_task")

    def test_put_status_ok(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = (
            '{"result":{"message": "success"}}')
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertEqual(snow.put(
                "api/now/table/sc_task/1", {"status": "start"}
            ), {"message": "success"})

    def test_put_no_msg(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 204
        m.return_value.read.return_value = ''
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertIsNone(snow.put(
                "api/now/table/sc_task/1", {"status": "start"}
            ))

    def test_put_wrong_status(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 201
        m.return_value.msg = 'Created'
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertEqual(snow.put(
                "api/now/table/sc_task/1", {"status": "start"}
            ), {'error': {'code': 201, 'message': 'Created'}})

    def test_put_wrong_json(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = 'Returned text'
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.DecodeError):
                snow.put("api/now/table/sc_task/1", {"status": "start"})

    def test_put_error_403(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 403, 'Forbidden', None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.put("api/now/table/sc_task/1", {"status": "start"})

    def test_put_error_404(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 404, 'Not Found', None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.put("api/now/table/sc_task/1", {"status": "start"})

    def test_put_error_500(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 500,
                                          'Internal Server Error',
                                          None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.put("api/now/table/sc_task/1", {"status": "start"})

    def test_put_error_505(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 505,
                                          'HTTP Version not supported',
                                          None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.put("api/now/table/sc_task/1", {"status": "start"})

    def test_post_status_ok(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 201
        m.return_value.read.return_value = (
            '{"result":{"success": "true"}}')
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertEqual(snow.post(
                "api/now/table/sc_task", {"task": {"id": 1}}
            ), {"success": "true"})

    def test_post_no_msg(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 204
        m.return_value.read.return_value = ''
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertIsNone(snow.post(
                "api/now/table/sc_task", {"task": {"id": 1}}
            ))

    def test_post_wrong_status(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.msg = 'OK'
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertEqual(snow.post(
                "api/now/table/sc_task", {"task": {"id": 1}}
            ), {'error': {'code': 200, 'message': 'OK'}})

    def test_post_wrong_json(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 201
        m.return_value.read.return_value = 'Returned text'
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.DecodeError):
                snow.post("api/now/table/sc_task", {"task": {"id": 1}})

    def test_post_error_403(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 403, 'Forbidden', None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.post("api/now/table/sc_task", {"task": {"id": 1}})

    def test_post_error_404(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 404, 'Not Found', None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.post("api/now/table/sc_task", {"task": {"id": 1}})

    def test_post_error_500(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 500,
                                          'Internal Server Error',
                                          None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.post("api/now/table/sc_task", {"task": {"id": 1}})

    def test_post_error_505(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 505,
                                          'HTTP Version not supported',
                                          None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.post("api/now/table/sc_task", {"task": {"id": 1}})

    def test_delete_status_ok(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = (
            '{"result":{"success": "true"}}')
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertEqual(
                snow.delete("api/now/table/sc_task/1"),
                {"success": "true"})

    def test_delete_no_msg(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 204
        m.return_value.read.return_value = ''
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertIsNone(snow.delete("api/now/table/sc_task/1"))

    def test_delete_wrong_status(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 207
        m.return_value.msg = 'Multi-Status'
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            self.assertEqual(
                snow.delete("api/now/table/sc_task/1"),
                {'error': {'code': 207, 'message': 'Multi-Status'}})

    def test_delete_wrong_json(self):
        m = mock.Mock()
        m.return_value.getcode.return_value = 200
        m.return_value.read.return_value = 'Returned text'
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.DecodeError):
                snow.delete("api/now/table/sc_task/1")

    def test_delete_error_403(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 403, 'Forbidden', None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.delete("api/now/table/sc_task/1")

    def test_delete_error_404(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 404, 'Not Found', None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.delete("api/now/table/sc_task/1")

    def test_delete_error_500(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 500,
                                          'Internal Server Error',
                                          None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.delete("api/now/table/sc_task/1")

    def test_delete_error_505(self):
        m = mock.Mock()
        m.side_effect = urllib2.HTTPError('', 505,
                                          'HTTP Version not supported',
                                          None, None)
        with mock.patch('urllib2.OpenerDirector.open', m, create=True):
            snow = servicenow.ServiceNow("url", "user", "pass")
            with self.assertRaises(servicenow.HTTPError):
                snow.delete("api/now/table/sc_task/1")
