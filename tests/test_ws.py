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
import servicenow.ws # noqa


class TestCaseServicenowWebService(unittest.TestCase):
    def test_get(self):
        m = mock.Mock()
        m.return_value = [{"sys_id":"123", "name":"toto"}]
        with mock.patch(
                "servicenow.ServiceNow._call", m, create=True):
            snow = servicenow.ws.ServiceNow("http://h:1", "user", "pass")
            self.assertEqual(snow.get('u_goal_uh/123', display_value=True, display_variables=False, limit=1), [{"sys_id":"123", "name":"toto"}])
        m.assert_called_with('GET', 'http://h:1/u_goal_uh.do?JSONv2&displayvalue=True&displayvariables=False&sysparm_limit=1&sysparm_sys_id=123', status_codes=(200,))

    def test_put(self):
        m = mock.Mock()
        m.return_value = [{"sys_id":"123", "name":"toto"}]
        with mock.patch(
                "servicenow.ServiceNow._call", m, create=True):
            snow = servicenow.ws.ServiceNow("http://h:1", "user", "pass")
            self.assertEqual(snow.put('u_goal_uh/123', {'name':'toto'}), [{"sys_id":"123", "name":"toto"}])
        m.assert_called_with('POST', 'http://h:1/u_goal_uh.do?JSONv2&sysparm_action=update&sysparm_query=sys_id%3D123', status_codes=(200, 204), params={'name': 'toto'})

    def test_put_no_sysid(self):
            snow = servicenow.ws.ServiceNow("http://h:1", "user", "pass")
            with self.assertRaises(ValueError) as e:
                snow.put('u_goal_uh', {'name':'toto'})
            self.assertEqual(str(e.exception), 'no sys_id specified on u_goal_uh')

    def test_post(self):
        m = mock.Mock()
        m.return_value = [{"sys_id":"123", "name":"toto"}]
        with mock.patch(
                "servicenow.ServiceNow._call", m, create=True):
            snow = servicenow.ws.ServiceNow("http://h:1", "user", "pass")
            self.assertEqual(snow.post('u_goal_uh', {"sys_id":"123", "name":"toto"}), [{"sys_id":"123", "name":"toto"}])
        m.assert_called_with('POST', 'http://h:1/u_goal_uh.do?JSONv2&sysparm_action=insert', status_codes=(200, 204), params={"sys_id":"123", "name":"toto"})

    def test_delete(self):
        m = mock.Mock()
        m.return_value = []
        with mock.patch(
                "servicenow.ServiceNow._call", m, create=True):
            snow = servicenow.ws.ServiceNow("http://h:1", "user", "pass")
            self.assertEqual(snow.delete('u_goal_uh/123'), [])
        m.assert_called_with('POST', 'http://h:1/u_goal_uh.do?JSONv2&sysparm_action=deleteRecord&sysparm_sys_id=123', status_codes=(200, 202, 204))

    def test_delete_no_sysid(self):
            snow = servicenow.ws.ServiceNow("http://h:1", "user", "pass")
            with self.assertRaises(ValueError) as e:
                snow.delete('u_goal_uh')
            self.assertEqual(str(e.exception), 'no sys_id specified on u_goal_uh')

if __name__ == '__main__':
    import logging
    logger = logging.getLogger()
    logger.setLevel(logging.WARN)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-s %(funcName)s:%(lineno)d %(message)s")

    handler_console = logging.StreamHandler()
    handler_console.setFormatter(formatter)
    handler_console.setLevel(logging.WARN)
    logger.addHandler(handler_console)
    unittest.main()
