from django.contrib import admin

from .models import Announcement


class AnnouncementAdmin(admin.ModelAdmin):

    list_display = ('text', 'level', 'is_active')
    list_filter = ('level', 'is_active')

admin.site.register(Announcement, AnnouncementAdmin)
