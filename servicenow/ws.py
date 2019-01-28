#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import servicenow

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote


class ServiceNow(servicenow.ServiceNow):
    """Handles and requests ServiceNow instance"""

    def _url_rewrite(self, path, **kwargs):
        """Reformat URL

        Arguments from WebService are available:
         - action = [get,getKeys,getRecords,insert,update]
         - sys_id
        """

        url = path + '.do?JSONv2'
        if 'display_value' in kwargs:
            url += '&displayvalue={display_value}'.format(**kwargs)
            del kwargs['display_value']
        if 'display_variables' in kwargs:
            url += '&displayvariables={display_variables}'.format(**kwargs)
            del kwargs['display_variables']
        opts = []
        for k, v in sorted(kwargs.items()):
            if v is not None:
                try:
                    opts.append('sysparm_{0}={1}'.format(k, quote(v)))
                except (AttributeError, TypeError):
                    opts.append('sysparm_{0}={1}'.format(k, v))
        if len(opts) > 0:
            url += "&{0}".format("&".join(opts))
        return "{0}/{1}".format(self.url, url)

    def get(self, path, **kwargs):
        if len(path.split('/')) > 1:
            kwargs['sys_id'] = path.split('/')[-1]
            path = path.split('/')[0]
        path = self._url_rewrite(path, **kwargs)
        return self._call('GET', path, status_codes=(200,))

    def put(self, path, params, **kwargs):
        if 'query' not in kwargs:
            if len(path.split('/')) < 2:
                raise ValueError('no sys_id specified on {0}'.format(path))
            kwargs['query'] = 'sys_id={0}'.format(path.split('/')[1])
            path = path.split('/')[0]
        return self._call('POST',
                          self._url_rewrite(path, action='update', **kwargs),
                          params=params,
                          status_codes=(200, 204))

    def post(self, path, params, **kwargs):
        return self._call('POST',
                          self._url_rewrite(path, action='insert', **kwargs),
                          params=params,
                          status_codes=(200, 204))

    def delete(self, path):
        if len(path.split('/')) < 2:
            raise ValueError('no sys_id specified on {0}'.format(path))
        sys_id = path.split('/')[-1]
        path = path.split('/')[0]
        return self._call('POST',
                          self._url_rewrite(path, action='deleteRecord',
                                            sys_id=sys_id),
                          status_codes=(200, 202, 204))

    update = put
    insert = post

API = ServiceNow
