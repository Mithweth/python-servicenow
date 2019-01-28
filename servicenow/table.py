#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import servicenow
import logging
import re
import time


try:
    text_type = str
except ImportError:
    text_type = unicode


class ServiceNow(servicenow.ServiceNow):
    """Handles and requests ServiceNow instance"""
    def __init__(self, url, username, password, proxy=None, verify=True):
        super(ServiceNow, self).__init__(url,
                                         username,
                                         password,
                                         proxy,
                                         verify)
        self._cache = {}

    def sysid_to_value(self, table, sysid):
        """Retrieve the display value from a Sys ID

        Needs read-only rights (or greater) on sys_dictionary and
        sys_db_object tables
        """
        key = table + '.' + sysid
        if key not in self._cache:
            self._cache[key] = super(ServiceNow,
                                     self).sysid_to_value(table,
                                                          sysid)
        return self._cache[key]

    def value_to_sysid(self, table, value):
        """Retrieve the Sys ID from a given display value

        Needs read-only rights (or greater) on sys_dictionary and
        sys_db_object tables
        """
        key = table + '.' + value
        if key not in self._cache:
            self._cache[key] = super(ServiceNow,
                                     self).value_to_sysid(table,
                                                          value)
        return self._cache[key]

    def Table(self, table):
        return Table(self, table)


class Table(object):
    def __init__(self, snow, table):
        self.snow = snow
        self.table = table
        self._default_pagesize = 30
        self.__logger = logging.getLogger('servicenow')

    def __repr__(self):
        return 'Table({0})'.format(self.table)

    def __getitem__(self, index):
        if index < 0:
            return None
        result = self.snow.get(self.table,
                               display_value='all',
                               offset=index, limit=1)
        if len(result) == 0:
            return None
        return TableRow(self, result[0])

    def __iter__(self):
        return iter(TableIterator(self.snow, self.table))

    def __len__(self):
        min = 0
        max = 65536
        res = self.snow.get(self.table,
                            offset=max,
                            limit=1)
        while len(res) == 1:
            (min, max) = (max, max * 2)
            res = self.snow.get(self.table,
                                offset=max,
                                limit=1)
        res = []
        while len(res) != 1:
            offset = int((max + min) / 2)
            res = self.snow.get(self.table,
                                offset=offset, limit=2)
            if len(res) == 0:
                if offset == 0:
                    return 0
                max = offset
            else:
                min = offset
        return offset + 1

    def __delitem__(self, index):
        self.remove(self[index])

    def remove(self, item):
        if isinstance(item, dict):
            return self.snow.delete("{0}/{sys_id}".format(self.table, **item))
        else:
            return self.snow.delete("{0}/{1}".format(self.table, item))

    def insert(self, data, **kwargs):
        params = {}
        row = TableRow(self, data)
        for field in row:
            if field != 'sys_id':
                params[field] = row[field]
        return self.snow.post(self.table, params, **kwargs)

    def _prepare(self, *filters):
        if len([f for f in filters if len(f) > 0]) == 0:
            raise Exception('no filters found')
        kw = []
        for f in filters:
            if f == '':
                continue
            for op in ('!=', '=', 'LIKE', '<', '>', 'NOT%20IN',
                       'NOT%20LIKE', 'IN', 'STARTSWITH', 'ENDSWITH'):
                if op in f:
                    kw.append(re.search('(.*)({0})(.*)'.format(op), f))
                    break
            else:
                raise NotImplementedError(f)
        res = self.snow.get(self.table,
                            fields=','.join([g.group(1) for g in kw]),
                            limit=1)
        first = TableRow(self, res[0])
        query = []
        for g in kw:
            key, op, val = g.groups()
            if key not in first:
                raise KeyError(key)
            if first[key].link is not None:
                query.append(
                    "{0}{1}{2}^OR{0}.name{1}{2}".format(key, op, val))
                continue       
            res = self.snow.get(self.table, query=g.string, limit=1)
            choices = []
            if len(res) == 0:
                if self.snow._admin is True:
                    choices = self.snow.get(
                        'sys_choice',
                        fields='value',
                        query='name={0}^element={1}^label{2}{3}'.format(
                            self.table, key, op, val))
                else:
                    vals = [i.strip() for i in val.split(',')]
                    for row in self.filter(fields=key):
                        if row[key].display_value in vals:
                            choices.append({'value': row[key].value})
                            vals.remove(row[key].display_value)
                        if row[key].value in vals:
                            choices.append({'value': row[key].value})
                            vals.remove(row[key].value)
                        if len(vals) == 0:
                            break
            if len(choices) > 0:
                query.append("{0}IN{1}".format(
                    key,
                    ','.join([i['value'] for i in choices])))
            else:
                query.append(g.string)
        return "^".join(query)

    def search(self, *args):
        return TableIterator(self.snow, self.table,
                             query=self._prepare(*args))

    def filter(self, **kwargs):
        return TableIterator(self.snow, self.table, **kwargs)


class TableIterator(object):
    def __init__(self, snow, table, **opts):
        self._default_pagesize = 30
        self.snow = snow
        self.table = table
        self.opts = opts

    def __iter__(self):
        kwargs = dict(self.opts)
        record_limit = kwargs.get('limit')
        record = 0
        kwargs['limit'] = self._default_pagesize
        kwargs['offset'] = 0
        kwargs['display_value'] = kwargs.get('display_value', 'all')
        while True:
            time_start = time.time()
            results = self.snow.get(self.table, **kwargs)
            time_elapsed = time.time() - time_start
            for row in results:
                if record_limit is not None and record == record_limit:
                    raise StopIteration
                record += 1
                yield TableRow(self, row)
            if len(results) < kwargs['limit']:
                raise StopIteration
            kwargs['offset'] += kwargs['limit']
            kwargs['limit'] = int(max(1, kwargs['limit'] * 0.8 / time_elapsed))


class TableRow(dict):
    def __init__(self, parent, data):
        obj = dict()
        for key in data:
            if isinstance(data[key], dict):
                obj[key] = TableRowField(**data[key])
            else:
                obj[key] = TableRowField(value=data[key])
        super(TableRow, self).__init__(obj)
        self.__dict__ = obj
        self._parent = parent

    def __eq__(self, data):
        for k in self:
            if k.startswith("sys_"):
                continue
            if k not in data:
                return False
            if self[k] != data[k]:
                return False
        for k in data:
            if k.startswith("sys_"):
                continue
            if k not in self:
                return False
        return True

    def __setitem__(self, name, value):
        if self[name] == self[name].value:
            self[name].value = value
        else:
            self[name].display_value = value
        if self._parent is not None:
            self._parent.snow.put(
                "{0}/{sys_id}".format(self._parent.table, **self),
                {name: value})


class TableRowField(text_type):
    def __new__(cls, link=None, display_value=None, value=None):
        if link is None or len(link) == 0 or \
                display_value is None or len(display_value) == 0:
            try:
                obj = text_type.__new__(cls, value)
            except UnicodeError:
                obj = text_type.__new__(cls, value.encode('utf-8'))
        else:
            try: 
                obj = text_type.__new__(cls, display_value)
            except UnicodeError:
                obj = text_type.__new__(cls, display_value.encode('utf-8'))
        obj.link = link
        obj.value = value
        obj.display_value = display_value
        if text_type != str:
            obj.__unicode__ = cls.__str__
            obj.__str__ = lambda self: self.__unicode__().encode('utf-8')
        return obj

    def __ne__(self, data):
        return not self.__eq__(data)

    def __eq__(self, data):
        if not isinstance(data, TableRowField):
            if self.link is None or len(self.link) == 0:
                return self.value == data
            else:
                return self.display_value == data
        elif self.value == data.value and \
                self.display_value == data.display_value:
            return True
        return False


API = ServiceNow
