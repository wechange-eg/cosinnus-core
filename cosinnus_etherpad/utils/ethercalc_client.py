import datetime
import json
import re
from builtins import object, range, str

import requests

basedate = datetime.date(1899, 12, 30)
basedatetime = datetime.datetime(1899, 12, 30)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass
    try:
        import unicodedata

        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
    return False


def set(coord, item):
    if isinstance(item, float):
        return 'set %s value n %f' % (coord, item)
    elif isinstance(item, int):
        return 'set %s value n %d' % (coord, item)
    elif isinstance(item, str) or isinstance(item, str):
        if item == '':
            return 'set %s empty' % coord
        elif item[0] == "'":
            return 'set %s text t %s' % (coord, item[1:])
        elif item[0] == '=':
            return 'set %s formula %s' % (coord, item[1:])
        elif is_number(item):
            return 'set %s value n %s' % (coord, item[1:])
        return 'set %s text t %s' % item


def ss_to_xy(s):
    """convert spreadsheet coordinates to zero-index xy coordinates.
    return None if input is invalid"""
    result = re.match(r'\$*([A-Z]+)\$*([0-9]+)', s, re.I)
    if result == None:
        return None
    xstring = result.group(1).upper()
    multiplier = 1
    x = 0
    for i in xstring:
        x = x * multiplier + (ord(i) - 64)
        multiplier = multiplier * 26
    x = x - 1
    y = int(result.group(2)) - 1
    return (x, y)


def _grid_size(cells):
    maxx = -1
    maxy = -1
    for k, v in list(cells.items()):
        (x, y) = ss_to_xy(k)
        maxx = max(x, maxx)
        maxy = max(y, maxy)
    return (maxx + 1, maxy + 1)


class EtherCalc(object):
    verify = True

    def __init__(self, url_root, verify=True):
        self.root = url_root
        self.verify = verify

    def get(self, cmd):
        r = requests.get(self.root + '/_' + cmd, verify=self.verify)
        r.raise_for_status()
        return r

    def post(self, id, data, content_type):
        r = requests.post(self.root + '/_' + id, data=data, headers={'Content-Type': content_type}, verify=self.verify)
        r.raise_for_status()
        return r

    def put(self, id, data, content_type):
        r = requests.put(self.root + '/_' + id, data=data, headers={'Content-Type': content_type}, verify=self.verify)
        r.raise_for_status()
        return r

    def cells(self, page, coord=None):
        api = '/%s/cells' % page
        if coord != None:
            api = api + '/' + coord
        return self.get(api).json()

    def command(self, page, command):
        r = requests.post(self.root + '/_/%s' % page, json={'command': command}, verify=self.verify)
        r.raise_for_status()
        return r.json()

    def create(self, data, format='python', id=None):
        if id == None:
            id = ''
        else:
            id = '/' + id
        if format == 'python':
            return self.post(id, json.dumps({'snapshot': data}), 'application/json')
        elif format == 'json':
            return self.post(id, data, 'application/json')
        elif format == 'csv':
            return self.post(id, data, 'text/csv')
        elif format == 'socialcalc':
            return self.post(id, data, 'text/x-socialcalc')
        elif format == 'excel':
            return self.post(id, data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def update(self, data, format='python', id=None):
        if id == None:
            sid = ''
        else:
            sid = '/' + id
        if format == 'python':
            return self.put(sid, json.dumps({'snapshot': data}), 'application/json')
        elif format == 'json':
            return self.put(sid, data, 'application/json')
        elif format == 'csv':
            return self.put(sid, data, 'text/csv')
        elif format == 'socialcalc':
            if id == None:
                upload = {'snapshot': data}
            else:
                upload = {'room': id, 'snapshot': data}
            return self.post(id, json.dumps(upload), 'application/json')
        elif format == 'excel':
            return self.put(sid, data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def export(self, page, format='python'):
        if format == 'python':
            cells = self.cells(page)
            (sizex, sizey) = _grid_size(cells)
            grid = [[None for _ in range(sizex)] for _ in range(sizey)]
            for k, v in list(cells.items()):
                (x, y) = ss_to_xy(k)
                if v['valuetype'] == 'n':
                    grid[y][x] = float(v['datavalue'])
                elif v['valuetype'] == 'b':
                    grid[y][x] = None
                elif v['valuetype'] == 'nd':
                    grid[y][x] = basedate + datetime.timedelta(days=int(v['datavalue']))
                elif v['valuetype'] == 'ndt':
                    grid[y][x] = basedatetime + datetime.timedelta(days=float((v['datavalue'])))
                else:
                    grid[y][x] = str(v['datavalue'])
            return grid
        elif format == 'json':
            return self.get('/' + page + '/csv.json').text
        elif format == 'socialcalc':
            return self.get('/' + page).text
        elif format == 'html':
            return self.get('/' + page + '/html').text
        elif format == 'csv':
            return self.get('/' + page + '/csv').text
        elif format == 'xlsx':
            return self.get('/' + page + '/xlsx').text
        elif format == 'md':
            return self.get('/' + page + '/md').text
        else:
            raise ValueError


if __name__ == '__main__':
    import pprint

    pp = pprint.PrettyPrinter(indent=4)
    e = EtherCalc('http://localhost:8000')
    pp.pprint(e.cells('test'))
    pp.pprint(e.cells('test', 'A1'))
    pp.pprint(e.export('test'))
