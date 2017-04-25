# coding: utf8
import urllib2
import json


class DecodeError(Exception):
    def __init__(self, body, message):
        self.message = message
        self.text = str(body)

    def __str__(self):
        return self.message


class HTTPError(Exception):
    def __init__(self, url, code, msg):
        self.url = url
        self.code = code
        self.message = msg

    def __str__(self):
        if self.code is not None:
            return 'HTTP Error %s: %s' % (self.code, self.message)
        else:
            return 'HTTP Error: %s' % (self.code, self.message)


class ServiceNow(object):
    """Handles and requests ServiceNow instance"""
    def __init__(self, url, username, password,
                 http_proxy=None, https_proxy=None):
        self.url = url
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, self.url, username, password)
        self.proxies = {}
        if http_proxy:
            self.proxies['http'] = http_proxy
        if https_proxy:
            self.proxies['https'] = https_proxy
        self._opener = urllib2.build_opener(
            urllib2.HTTPBasicAuthHandler(password_mgr),
            urllib2.ProxyHandler(self.proxies)
        )

    def _call(self, method, path, params=None,
              status_codes=(200, 201, 204), **kwargs):
        url = "%s/%s" % (self.url, path)
        options = [
            'sysparm_%s=%s' % (k, v)
            for k, v in kwargs.iteritems()
            if v is not None
        ]
        if options:
            url += '&' if url.find('?') > -1 else '?'
            url += "&".join(options)
        request = urllib2.Request(url)
        request.get_method = lambda: method
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        if params:
            request.add_data(json.dumps(params))
        result = response = None
        try:
            response = self._opener.open(request)
        except urllib2.HTTPError as e:
            raise HTTPError(request.get_full_url(), e.code, e.msg)
        except urllib2.URLError as e:
            raise HTTPError(request.get_full_url(), None, e.reason)
        if response.getcode() not in status_codes:
            return {'error': {
                'code': response.getcode(),
                'message': response.msg
            }}
        response_data = response.read()
        if len(response_data) == 0:
            return None
        try:
            result = json.loads(response_data)
        except ValueError as e:
            raise DecodeError(response_data, e.message)
        if 'result' in result:
            result = result['result']
        return result

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
         - force_row_count
         - display_value
         - exclude_reference_link
         - offset
         - limit
        """
        return self._call(
            'GET',
            path,
            status_codes=(200,),
            **kwargs
        )

    def put(self, path, params):
        """Update an existing ServiceNow records"""
        return self._call(
            'PUT',
            path,
            params=params,
            status_codes=(200, 204)
        )

    def post(self, path, params):
        """Create a new ServiceNow record"""
        return self._call(
            'POST',
            path,
            params=params,
            status_codes=(201, 204)
        )

    def delete(self, path):
        """Delete an existing ServiceNow record"""
        return self._call(
            'DELETE',
            path,
            status_codes=(200, 202, 204)
        )
