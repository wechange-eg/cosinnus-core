# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from cosinnus_event.models import Event, Suggestion, Vote, ConferenceEvent
from cosinnus.admin import BaseTaggableAdmin, CosinnusConferenceSettingsInline


def restart_bbb_rooms(modeladmin, request, queryset):
    for event in queryset.all():
        try:
            bbb_room = event.media_tag.bbb_room
            bbb_room.restart()
        except:
            pass
restart_bbb_rooms.short_description = _('Restart BBB rooms')


class VoteInlineAdmin(admin.TabularInline):
    extra = 0
    list_display = ('from_date', 'to_date', 'event')
    model = Vote


class SuggestionAdmin(admin.ModelAdmin):
    inlines = (VoteInlineAdmin,)
    list_display = ('from_date', 'to_date', 'event', 'count')
    list_filter = ('event__state', 'event__creator', 'event__group',)
    readonly_fields = ('event', 'count')

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            # we create a new suggestion and the user should be able to select
            # an event.
            return [x for x in self.readonly_fields if x != 'event']
        return super(SuggestionAdmin, self).get_readonly_fields(request, obj)


class SuggestionInlineAdmin(admin.TabularInline):
    extra = 0
    list_display = ('from_date', 'to_date', 'event', 'count')
    model = Suggestion
    readonly_fields = ('count',)

admin.site.register(Suggestion, SuggestionAdmin)


class EventAdmin(BaseTaggableAdmin):
    list_display = BaseTaggableAdmin.list_display + ['id', 'from_date', 'to_date', 'group', 'state', 'is_hidden_group_proxy']
    list_filter = BaseTaggableAdmin.list_filter + ['state', 'is_hidden_group_proxy']
    inlines = BaseTaggableAdmin.inlines + [SuggestionInlineAdmin, CosinnusConferenceSettingsInline]
    actions = (restart_bbb_rooms, )

admin.site.register(Event, EventAdmin)


class ConferenceEventAdmin(BaseTaggableAdmin):
    list_display = BaseTaggableAdmin.list_display + ['id', 'type', 'room', 'from_date', 'to_date', 'group', 'state']
    list_filter = BaseTaggableAdmin.list_filter + ['type', ]
    actions = (restart_bbb_rooms, )
    inlines = [CosinnusConferenceSettingsInline]
    raw_id_fields = BaseTaggableAdmin.raw_id_fields + ['presenters']
    inline_reverse = []

admin.site.register(ConferenceEvent, ConferenceEventAdmin)
