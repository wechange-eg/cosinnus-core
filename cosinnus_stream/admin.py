# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from cosinnus_stream.models import Stream


class StreamAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'created')
    search_fields = ('title',)


admin.site.register(Stream, StreamAdmin)

