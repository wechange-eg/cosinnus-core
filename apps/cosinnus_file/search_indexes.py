# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.utils.search import BaseHierarchicalTaggableObjectIndex

from cosinnus_file.models import FileEntry


class FileEntryIndex(BaseHierarchicalTaggableObjectIndex, indexes.Indexable):

    def get_model(self):
        return FileEntry
    
    def index_queryset(self, using=None):
        qs = super(FileEntryIndex, self).index_queryset(using=using)
        # exclude attached files from search index
        qs = qs.exclude(path__exact='/attachments/')
        return qs

