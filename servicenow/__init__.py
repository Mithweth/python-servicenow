#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# -*- coding: utf-8 -*-

import sys
import json

if sys.version_info >= (3, 0):
    import urllib.request as compat_urllib
    import urllib.parse as compat_parse
else:
    import urllib2 as compat_urllib
    import urllib as compat_parse


class DecodeError(Exception):
    def __init__(self, body, message):
        self.message = message
        self.text = str(body)

    def __str__(self):
        return self.message


class HTTPError(Exception):
    def __init__(self, url, code, msg):
        self.url = url
        self.code = code if isinstance(code, int) else -1
        self.message = msg

    def __str__(self):
        return 'HTTP Error %s: %s' % (self.code, self.message)


class ReferenceNotFound(Exception):
    def __init__(self, value, table):
        self.value = value
        self.table = table

    def __str__(self):
        return '%s in %s' % (self.value, self.table)


class ServiceNow(object):
    """Handles and requests ServiceNow instance"""
    def __init__(self, url, username, password, proxy=None):
        self.url = url
        password_mgr = compat_urllib.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, self.url, username, password)
        if proxy:
            proxies = {'http': proxy, 'https': proxy}
        else:
            proxies = {}
        self._opener = compat_urllib.build_opener(
            compat_urllib.HTTPBasicAuthHandler(password_mgr),
            compat_urllib.ProxyHandler(proxies)
        )

    def _call(self, method, path, params=None,
              status_codes=(200, 201, 204), **kwargs):
        if len(path.split('/')) < 3:
            url = "%s/api/now/table/%s" % (self.url, path)
        else:
            url = "%s/%s" % (self.url, path)
        options = [
            'sysparm_%s=%s' % (k, v)
            for k, v in kwargs.items()
            if v is not None
        ]
        if options:
            url += '&' if url.find('?') > -1 else '?'
            url += "&".join(options)
        request = compat_urllib.Request(url)
        if sys.version_info >= (3, 3):
            request.method = method
        else:
            request.get_method = lambda: method
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        if params:
            if sys.version_info >= (3, 4):
                request.data = json.dumps(params).encode('utf-8')
            else:
                request.add_data(json.dumps(params))
        result = response = None
        try:
            response = self._opener.open(request)
        except compat_urllib.HTTPError as e:
            if sys.version_info >= (3, 4):
                raise HTTPError(request.full_url, e.code, e.msg)
            else:
                raise HTTPError(request.get_full_url(), e.code, e.msg)
        except compat_urllib.URLError as e:
            if sys.version_info >= (3, 4):
                raise HTTPError(request.full_url, None, e.reason)
            else:
                raise HTTPError(request.get_full_url(), None, e.reason)
        if response.getcode() not in status_codes:
            return {'error': {
                'code': response.getcode(),
                'message': response.msg
            }}
        tmp = response.read()
        if hasattr(tmp, "decode"):
            response_data = tmp.decode('utf-8', 'ignore')
        else:
            response_data = tmp
        if len(response_data) == 0:
            return None
        try:
            result = json.loads(response_data)
        except ValueError as e:
            raise DecodeError(response_data, str(e))
        if 'result' in result:
            result = result['result']
        return result

    def _display_field(self, table):
        """Returns the displayed field of any tables

        Needs read-only rights (or greater) on sys_dictionary and
        sys_db_object tables
        """
        sd = self.get('sys_dictionary?name=%s&display=true' % table)
        if len(sd) > 0:
            return sd[0]['element']
        obj = self.get('sys_db_object?name=%s' % table,
                       exclude_reference_link=True)
        if len(obj[0]['super_class']) == 0:
            elem = self.get('sys_dictionary?name=%s&element=name' % table)
            if len(elem) == 0:
                raise KeyError('name')
            return 'name'
        else:
            superclass = self.get('sys_db_object?sys_id=%s' %
                                  obj[0]['super_class'])
            return self._display_field(superclass[0]['name'])

    def tables(self):
        """List all available tables"""
        tables = self._call(
            'GET',
            '/api/now/table/sys_db_object'
        )
        return [table['name'] for table in tables]

    def get(self, path, **kwargs):
        """Queries ServiceNow

        Keywords arguments corresponds to ServiceNow parameters:
         - order
         - order_direction
         - fields
         - display_value
         - exclude_reference_link
         - offset
         - limit
        """
        return self._call('GET',
                          path,
                          status_codes=(200,),
                          **kwargs)

    def put(self, path, params, **kwargs):
        """Update an existing ServiceNow records

        Keywords arguments corresponds to ServiceNow parameters:
         - input_display_value
         - fields
         - display_value
         - exclude_reference_link
        """
        return self._call('PUT',
                          path,
                          params=params,
                          status_codes=(200, 204),
                          **kwargs)

    def post(self, path, params, **kwargs):
        """Create a new ServiceNow record

        Keywords arguments corresponds to ServiceNow parameters:
         - input_display_value
         - fields
         - display_value
         - exclude_reference_link
        """
        return self._call('POST',
                          path,
                          params=params,
                          status_codes=(201, 204),
                          **kwargs)

    def delete(self, path):
        """Delete an existing ServiceNow record"""
        return self._call('DELETE',
                          path,
                          status_codes=(200, 202, 204))

    def sysid_to_value(self, table, sysid):
        """Retrieve the display value from a Sys ID

        Needs read-only rights (or greater) on sys_dictionary and
        sys_db_object tables
        """
        try:
            field = self._display_field(table)
        except KeyError:
            raise ReferenceNotFound(sysid, table)
        search = self.get("%s/%s" % (table, sysid))
        if len(search) == 0:
            raise ReferenceNotFound(sysid, table)
        return search[field]

    def value_to_sysid(self, table, value):
        """Retrieve the Sys ID from a given display value

        Needs read-only rights (or greater) on sys_dictionary and
        sys_db_object tables
        """
        try:
            field = self._display_field(table)
        except KeyError:
            raise ReferenceNotFound(value, table)
        search = self.get("%s?%s=%s" % (table, field,
                                        compat_parse.quote(value)))
        if len(search) == 0:
            raise ReferenceNotFound(value, table)
        return search[0]['sys_id']

API = ServiceNow
