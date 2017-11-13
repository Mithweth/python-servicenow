# coding: utf8
import re
import sys
import byg_servicenow
if sys.version_info >= (3, 0):
    import urllib.parse as compat_parse
else:
    import urllib as compat_parse


class ServiceNow(byg_servicenow.ServiceNow):
    """Handles and requests ServiceNow instance"""
    def __init__(self, url, username, password,
                 http_proxy=None, https_proxy=None):
        super(self.__class__, self).__init__(url, username, password,
                                             http_proxy, https_proxy)
        self._cache = {}

    def sysid_to_value(self, table, sysid):
        """Retrieve the display value from a Sys ID

        Needs read-only rights (or greater) on sys_dictionary and
        sys_db_object tables
        """
        key = table + '.' + sysid
        if key not in self._cache:
            self._cache[key] = super(self.__class__,
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
            self._cache[key] = super(self.__class__,
                                     self).value_to_sysid(table,
                                                          value)
        return self._cache[key]

    def Table(self, table):
        return Table(self, table)


class Table(object):
    def __init__(self, snow, table):
        self.snow = snow
        self.table = table
        self.display_value = False

    def __repr__(self):
        return 'Table(%s)' % self.table

    def __getitem__(self, index):
        if index < 0:
            return None
        result = self.snow.get(self.table,
                               display_value=self.display_value,
                               offset=index, limit=1)
        if len(result) == 0:
            return None
        return self.TableRow(self, result[0])

    def __iter__(self):
        for row in self.snow.get(self.table,
                                 display_value=self.display_value):
            yield self.TableRow(self, row)

    def __len__(self):
        min = 0
        max = 65536
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
        self.snow.delete("%s/%s" % (self.table, item['sys_id']))

    def insert(self, data):
        params = {}
        row = self.TableRow(self, data)
        for field in row:
            if field != 'sys_id':
                params[field] = row[field]
        self.snow.post(self.table, params)
        return row

    def search(self, *filters):
        query = []
        for f in filters:
            if f == '':
                continue
            if '!=' in f:
                g = re.search('(.*)(!=)(.*)', f)
            elif 'LIKE' in f:
                g = re.search('(.*)(LIKE)(.*)', f)
            elif '=' in f:
                g = re.search('(.*)(=)(.*)', f)
            else:
                raise AttributeError('operator not implemented')
            v = g.group(3)
            first = self[0]
            if len(first) == 0:
                yield []
            if g.group(1) not in first:
                raise KeyError(g.group(1))
            if isinstance(first.__dict__[g.group(1)], dict):
                v = self.snow.value_to_sysid(
                    first.__dict__[g.group(1)]['link'].split('/')[-2], v)
            query.append("%s%s%s" % (g.group(1), g.group(2), v))
        params = {'sysparm_query': "^".join(query)}
        for row in self.snow.get("%s?%s" % (self.table,
                                            compat_parse.urlencode(params)),
                                 display_value=self.display_value):
            yield self.TableRow(self, row)

    class TableRow(object):
        def __init__(self, parent, data):
            self.__dict__ = dict(**data)
            self.snow = parent.snow
            self.table = parent.table
            self.__data = data

        def __repr__(self):
            try:
                sysid = self.__data['sys_id']
            except KeyError:
                sysid = None
            return 'TableRow(ID: %s, Table: %s)' % (sysid, self.table)

        def __eq__(self, data):
            for k in self.__data:
                if k.startswith("sys_"):
                    continue
                if k not in data:
                    return False
                if self.__data[k] != data[k]:
                    return False
            for k in data:
                if k not in self.__data:
                    return False
                if self.__data[k] != data[k]:
                    return False
            return True

        def __str__(self):
            results = {}
            for k in self.__data:
                results[k] = self[k]
            return str(results)

        def __len__(self):
            if self.__data:
                return len(self.__data)
            return 0

        def __iter__(self):
            for k in self.__data:
                yield k

        def __contains__(self, key):
            if key in self.__data:
                return True
            return False

        def __getitem__(self, name):
            if name not in self.__data:
                raise KeyError(name)
            if not isinstance(self.__data[name], dict):
                return self.__data[name]
            elif "display_value" in self.__data[name]:
                return self.__data[name]["display_value"]
            elif name == "sys_domain":
                return self.__data[name]["value"]
            elif "link" not in self.__data[name]:
                return None
            return self.snow.sysid_to_value(
                self.__data[name]["link"].split('/')[-2],
                self.__data[name]["link"].split('/')[-1])

        def __setitem__(self, name, value):
            params = {}
            self.__data[name] = value
            for k in self:
                params[k] = self[k]
            self.snow.put("%s/%s" % (self.table, self.__data['sys_id']),
                          params)
