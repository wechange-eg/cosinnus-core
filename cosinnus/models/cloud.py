import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from django.utils.html import escape

from cosinnus.conf import settings
from cosinnus_cloud.utils.nextcloud import perform_fulltext_search


@dataclass
class NextcloudFileProxy:
    name: str
    url: str
    excerpt: str
    created: dt.datetime


class NextcloudFulltextSearchQuerySet(Sequence):
    """A minimal implementation of Django QuerySet that calls the Nextcloud fulltext search
    when an item is accessed. Used by QuickSearchAPIView.
    """

    def __init__(self, user, query, page=1, page_size=20):
        self.user = user
        self.query = query
        self.page = page
        self.page_size = page_size
        self._results = None

    def all(self):
        return self

    def _execute_query(self):
        self._results = []
        try:
            response = perform_fulltext_search(self.user, self.query, page=self.page, page_size=self.page_size)
        except Exception:
            return
        else:
            for doc in response['documents']:
                try:
                    excerpt = escape(doc['excerpts'][0]['excerpt'])
                except LookupError:
                    excerpt = ''
                self._results.append(
                    NextcloudFileProxy(
                        name=escape(doc['info']['path']),
                        url=f"{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}{doc['link']}",
                        created=dt.datetime.fromtimestamp(doc['info']['mtime'], dt.timezone.utc),
                        excerpt=excerpt,
                    )
                )

    def __getitem__(self, item):
        if self._results is None:
            self._execute_query()
        return self._results[item]

    def __len__(self):
        if self._results is None:
            self._execute_query()
        return len(self._results)
