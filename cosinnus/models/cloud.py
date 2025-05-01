import datetime as dt
from dataclasses import dataclass


@dataclass
class NextcloudFileProxy:
    name: str
    url: str
    excerpt: str
    created: dt.datetime
