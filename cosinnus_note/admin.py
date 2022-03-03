# -*- coding: utf-8 -*-
from django.contrib import admin

from cosinnus_note.models import Note
from cosinnus.admin import BaseTaggableAdmin


class NoteModelAdmin(BaseTaggableAdmin):
    list_display = BaseTaggableAdmin.list_display + ['short_text', ]
    search_fields = BaseTaggableAdmin.search_fields + ['text', ]
    
admin.site.register(Note, NoteModelAdmin)
