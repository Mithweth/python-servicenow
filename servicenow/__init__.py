# coding: utf8
import sys
if sys.version_info >= (3, 0):
    import urllib.request as urllib2
else:
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
        self.code = code if isinstance(code, int) else -1
        self.message = msg

    def __str__(self):
        return 'HTTP Error %s: %s' % (self.code, self.message)


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
        if '/' not in path:
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
        request = urllib2.Request(url)
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
        except urllib2.HTTPError as e:
            if sys.version_info >= (3, 4):
                raise HTTPError(request.full_url, e.code, e.msg)
            else:
                raise HTTPError(request.get_full_url(), e.code, e.msg)
        except urllib2.URLError as e:
            if sys.version_info >= (3, 4):
                raise HTTPError(request.full_url, None, e.reason)
            else:
                raise HTTPError(request.get_full_url(), None, e.reason)
        if response.getcode() not in status_codes:
            return {'error': {
                'code': response.getcode(),
                'message': response.msg
            }}
        response_data = response.read().decode('utf-8', 'ignore')
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
         - fields
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

    def put(self, path, params, **kwargs):
        """Update an existing ServiceNow records

        Keywords arguments corresponds to ServiceNow parameters:
         - input_display_value
         - fields
         - display_value
         - exclude_reference_link
        """
        return self._call(
            'PUT',
            path,
            params=params,
            status_codes=(200, 204),
            **kwargs
        )

    def post(self, path, params, **kwargs):
        """Create a new ServiceNow record

        Keywords arguments corresponds to ServiceNow parameters:
         - input_display_value
         - fields
         - display_value
         - exclude_reference_link
        """
        return self._call(
            'POST',
            path,
            params=params,
            status_codes=(201, 204),
            **kwargs
        )

    def delete(self, path):
        """Delete an existing ServiceNow record"""
        return self._call(
            'DELETE',
            path,
            status_codes=(200, 202, 204)
        )
