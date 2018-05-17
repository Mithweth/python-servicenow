#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import re
import sys
import servicenow


class ServiceNow(servicenow.ServiceNow):
    """Handles and requests ServiceNow instance"""

    def _url_rewrite(self, path, **kwargs):
        """Reformat URL

        Arguments from WebService are available:
         - action = [get,getKeys,getRecords,insert,update]
         - sys_id
        """

        url = path + '.do?JSONv2&'
        if 'display_value' in kwargs:
            url += 'displayvalue=%s' % kwargs['display_value']
            del kwargs['display_value']
        if 'display_variables' in kwargs:
            url += 'displayvariables=%s' % kwargs['display_variables']
            del kwargs['display_variables']
        options = [
            'sysparm_%s=%s' % (k, v)
            for k, v in kwargs.items()
            if v is not None
        ]
        if options:
            url += "&".join(options)
        return "%s/%s" % (self.url, url)

    def get(self, path,
            display_variables=False,
            display_value=False, **kwargs):
        if len(path.split('/')) > 1:
            kwargs['sys_id'] = path.split('/')[-1]
            path = path.split('/')[0]
        path = self._url_rewrite(path, **kwargs)
        path += "&displayvalue=%s" % display_value
        path += "&displayvariables=%s" % display_variables
        return self._call('GET', path, status_codes=(200,))

    def put(self, path, params, **kwargs):
        if 'query' not in kwargs:
            if len(path.split('/')) < 2:
                raise ValueError('no sys_id specified on %s' % path)
            kwargs['query'] = 'sys_id=' + path.split('/')[1]
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
            raise ValueError('no sys_id specified on %s' % path)
        sys_id = path.split('/')[-1]
        path = path.split('/')[0]
        return self._call('POST',
                          self._url_rewrite(path, action='deleteRecord',
                                            sys_id=sys_id),
                          status_codes=(200, 202, 204))

    update = put
    insert = post

API = ServiceNow
