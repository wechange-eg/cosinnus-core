# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from cosinnus_file.models import FileEntry
from cosinnus.admin import BaseHierarchicalTaggableAdmin


class FileEntryAdmin(BaseHierarchicalTaggableAdmin):
    list_display = BaseHierarchicalTaggableAdmin.list_display + ['_sourcefilename']
    search_fields = BaseHierarchicalTaggableAdmin.search_fields + ['_sourcefilename']

admin.site.register(FileEntry, FileEntryAdmin)
