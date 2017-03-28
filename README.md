# python-servicenow

Handles and requests ServiceNow instance

## Installation

`python setup.py install`

## Unit tests

`python setup.py test`

## Usage

```
from servicenow import ServiceNow
sn = ServiceNow("http://service-now.com", 'foo', 'foo_pass')
sn.get('api/now/table/sc_tasks')
```
