#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import json
import logging
import ssl

try:
    from urllib.request import HTTPPasswordMgrWithDefaultRealm, HTTPSHandler
    from urllib.request import HTTPBasicAuthHandler, ProxyHandler
    from urllib.request import build_opener, Request
    from urllib.error import HTTPError, URLError
    from http.client import BadStatusLine
    from urllib.parse import quote
except ImportError:
    from urllib2 import HTTPPasswordMgrWithDefaultRealm, HTTPSHandler
    from urllib2 import HTTPBasicAuthHandler, ProxyHandler
    from urllib2 import build_opener, Request, HTTPError, URLError
    from httplib import BadStatusLine
    from urllib import quote


class ServiceNowDecodeError(Exception):
    def __init__(self, body, message):
        self.message = message
        self.text = str(body)

    def __str__(self):
        return self.message


class ServiceNowHttpError(Exception):
    def __init__(self, url, code, msg, content=None):
        self.url = url
        self.code = code if isinstance(code, int) else -1
        self.message = msg
        self.content = content

    def __str__(self):
        return 'HTTP Error {0}: {1}, {2}'.format(
            self.code, self.message, self.url)


class ServiceNowReferenceNotFound(Exception):
    def __init__(self, value, table):
        self.value = value
        self.table = table

    def __str__(self):
        return '{0} in {1}'.format(self.value, self.table)


class ServiceNow(object):
    """Handles and requests ServiceNow instance"""
    def __init__(self, url, username, password, proxy=None, verify=True):
        self.url = url
        self._logger = logging.getLogger('servicenow')
        password_mgr = HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, self.url, username, password)
        handlers = []
        if verify is False:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            handlers.append(HTTPSHandler(context=ctx))
        handlers.append(HTTPBasicAuthHandler(password_mgr))
        if proxy is not None:
            handlers.append(ProxyHandler(
                {'http': proxy, 'https': proxy}))
        self._opener = build_opener(*handlers)
        self.__admin = None

    @property
    def _admin(self):
        if self.__admin is None:
            res = self.get('sys_choice', fields='value', limit=1)
            if len(res) == 0 or 'value' not in res[0]:
                self.__admin = False
            else:
                self.__admin = True
        return self.__admin   

    def _call(self, method, url, params=None,
              status_codes=(200, 201, 204)):
        self._logger.info('%s %s', method.upper(), url)
        request = Request(url)
        request.get_method = lambda: method
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        if params:
            request.data = json.dumps(params).encode('utf-8')
            self._logger.debug('Body: %s', json.dumps(params))
        result = response = None
        try:
            response = self._opener.open(request)
        except HTTPError as e:
            try:
                content = e.read()
            except:
                content = None
            raise ServiceNowHttpError(request.get_full_url(), e.code,
                                      e.msg, content)
        except BadStatusLine as e:
            raise ServiceNowHttpError(request.get_full_url(), None, e.line)
        except URLError as e:
            raise ServiceNowHttpError(request.get_full_url(), None, e.reason)
        self._logger.debug('Status Code: %d', response.getcode())
        if response.getcode() not in status_codes:
            return {'error': {
                'code': response.getcode(),
                'message': response.msg
            }}
        tmp = response.read()
        if len(tmp) > 1024:
            self._logger.debug('Response: %s...', tmp[:1024])
        else:
            self._logger.debug('Response: %s', tmp)
        try:
            response_data = tmp.decode('utf-8', 'ignore')
        except AttributeError:
            response_data = tmp
        if len(response_data) == 0:
            return None
        try:
            result = json.loads(response_data)
        except ValueError as e:
            raise ServiceNowDecodeError(response_data, str(e))
        for field in ('result', 'records'):
            if field in result:
                result = result[field]
        return result

    def _url_rewrite(self, path, **kwargs):
        if len(path.split('/')) < 3:
            url = "{0}/api/now/table/{1}".format(self.url, path)
        else:
            url = "{0}/{1}".format(self.url, path)
        opts = []
        if 'order' in kwargs:
            query_suffix = 'ORDERBY'
            if 'order_direction' in kwargs:
                if kwargs['order_direction'].lower() not in ('asc', 'desc'):
                    raise ValueError('order_directory must be asc or desc')
                if kwargs['order_direction'].lower() == 'desc':
                    query_suffix = 'ORDERBYDESC'
                del kwargs['order_direction']
            kwargs['query'] = '{0}^{1}'.format(
                kwargs.get('query', ''),
                '^'.join(['{0}{1}'.format(query_suffix, f)
                          for f in kwargs['order'].split(',')]))
            del kwargs['order']
        for k, v in sorted(kwargs.items()):
            if v is not None:
                try:
                    opts.append('sysparm_{0}={1}'.format(k, quote(v)))
                except (AttributeError, TypeError):
                    opts.append('sysparm_{0}={1}'.format(k, v))
        if len(opts) > 0:
            url += '&' if url.find('?') > -1 else '?'
            url += "&".join(opts)
        return url

    def _display_field(self, table):
        """Returns the displayed field of any tables

        Needs read-only rights (or greater) on sys_dictionary and
        sys_db_object tables
        """
        sd = self.get('sys_dictionary',
                      query='name={0}^display=true'.format(table),
                      fields='element')
        if len(sd) > 0:
            return sd[-1]['element']
        obj = self.get('sys_db_object',
                       query='name={0}'.format(table),
                       exclude_reference_link=True,
                       fields='super_class')
        if len(obj[0]['super_class']) == 0:
            elem = self.get('sys_dictionary',
                            query='name={0}^element=name'.format(table))
            if len(elem) == 0:
                raise KeyError('name')
            return 'name'
        else:
            scl = self.get('sys_db_object',
                           query='sys_id={super_class}'.format(**obj[0]),
                           fields='name')
            return self._display_field(scl[0]['name'])

    def tables(self):
        """List all available tables"""
        tables = self._call(
            'GET',
            self._url_rewrite('/sys_db_object')
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
                          self._url_rewrite(path, **kwargs),
                          status_codes=(200,))

    def put(self, path, params, **kwargs):
        """Update an existing ServiceNow records

        Keywords arguments corresponds to ServiceNow parameters:
         - input_display_value
         - fields
         - display_value
         - exclude_reference_link
        """
        return self._call('PUT',
                          self._url_rewrite(path, **kwargs),
                          params=params,
                          status_codes=(200, 204))

    def post(self, path, params, **kwargs):
        """Create a new ServiceNow record

        Keywords arguments corresponds to ServiceNow parameters:
         - input_display_value
         - fields
         - display_value
         - exclude_reference_link
        """
        return self._call('POST',
                          self._url_rewrite(path, **kwargs),
                          params=params,
                          status_codes=(201, 204))

    def delete(self, path):
        """Delete an existing ServiceNow record"""
        return self._call('DELETE',
                          self._url_rewrite(path),
                          status_codes=(200, 202, 204))

    def sysid_to_value(self, table, sysid):
        """Retrieve the display value from a Sys ID

        Needs read-only rights (or greater) on sys_dictionary and
        sys_db_object tables
        """
        try:
            field = self._display_field(table)
        except KeyError:
            raise ServiceNowReferenceNotFound(sysid, table)
        search = self.get("{0}/{1}".format(table, sysid))
        if len(search) == 0:
            raise ServiceNowReferenceNotFound(sysid, table)
        self._logger.debug('%s(%s) = %s', table, sysid, search[field])
        return search[field]

    def value_to_sysid(self, table, value):
        """Retrieve the Sys ID from a given display value

        Needs read-only rights (or greater) on sys_dictionary and
        sys_db_object tables
        """
        try:
            field = self._display_field(table)
        except KeyError:
            raise ServiceNowReferenceNotFound(value, table)
        search = self.get("{0}".format(table),
                          query="{0}={1}".format(field, quote(value)))
        if len(search) == 0:
            raise ServiceNowReferenceNotFound(value, table)
        self._logger.debug('%s(%s) = %s', table, value, search[0]['sys_id'])
        return search[0]['sys_id']


API = ServiceNow
