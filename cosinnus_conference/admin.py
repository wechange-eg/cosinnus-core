# -*- coding: utf-8 -*-
""" The entire conference admin is hidden if conferences are not enabled! """

from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from cosinnus.admin import CosinnusProjectAdmin, \
    CosinnusConferenceSettingsInline
from cosinnus.conf import settings
from cosinnus.models.bbb_room import BBBRoom, BBBRoomVisitStatistics
from cosinnus.models.conference import CosinnusConferenceRoom, \
    ParticipationManagement, CosinnusConferenceApplication,\
    CosinnusConferencePremiumBlock
from cosinnus.models.group_extra import CosinnusConference


if settings.COSINNUS_CONFERENCES_ENABLED:

    def restart_bbb_rooms(modeladmin, request, queryset):
        for bbb_room in queryset.all():
            try:
                bbb_room.restart()
            except:
                pass
    
    
    restart_bbb_rooms.short_description = _('Restart')
    
    
    class CosinnusBBBRoomAdmin(admin.ModelAdmin):
        list_display = ('meeting_id', 'name', 'ended', 'portal')
        list_filter = ('ended', 'portal')
        search_fields = ('meeting_id', 'internal_meeting_id', 'name')
        readonly_fields = ('last_create_params',)
        actions = (restart_bbb_rooms, )
        change_form_template = 'admin/bbbroom/change_form.html'
        
    admin.site.register(BBBRoom, CosinnusBBBRoomAdmin)
    
    
    class CosinnusConferenceRoomAdmin(admin.ModelAdmin):
        list_display = ('title', 'id', 'type', 'group', 'sort_index')
        list_filter = ('group', 'group__portal')
        search_fields = ('slug', 'title',)
        inlines = [CosinnusConferenceSettingsInline]
    
    admin.site.register(CosinnusConferenceRoom, CosinnusConferenceRoomAdmin)
    
    class CosinnusParticipationManagementAdmin(admin.ModelAdmin):
        list_display = ('conference', 'application_start', 'application_end')
    
    admin.site.register(ParticipationManagement, CosinnusParticipationManagementAdmin)
    
    class CosinnusConferenceApplicationAdmin(admin.ModelAdmin):
        list_display = ('user_email', 'conference', 'status')
        search_fields = ('conference__name',)
    
    admin.site.register(CosinnusConferenceApplication, CosinnusConferenceApplicationAdmin)
    
    class BBBRoomVisitStatisticsAdmin(admin.ModelAdmin):
        list_display = ('user', 'bbb_room', 'group', 'visit_datetime')
        list_filter = ('bbb_room',)
        search_fields = ('bbb_room__name', 'group__name')
        
    admin.site.register(BBBRoomVisitStatistics, BBBRoomVisitStatisticsAdmin)
    
    
    class CosinnusConferencePremiumBlockInline(admin.StackedInline):
        model = CosinnusConferencePremiumBlock
        template = 'cosinnus/admin/conference_premium_block_help_text_stacked_inline.html'
        extra = 0
        
        
    class CosinnusConferenceAdmin(CosinnusProjectAdmin):
        
        actions = CosinnusProjectAdmin.actions + ['convert_to_project']
        inlines = CosinnusProjectAdmin.inlines + [
            CosinnusConferencePremiumBlockInline
        ]
        readonly_fields = ('created', 'last_modified', 'is_premium_currently',
                           'attached_objects')
        exclude = CosinnusProjectAdmin.exclude + ['enable_user_premium_choices_until',]
        
        def get_actions(self, request):
            actions = super(CosinnusConferenceAdmin, self).get_actions(request)
            del actions['convert_to_conference']
            return actions
    
    admin.site.register(CosinnusConference, CosinnusConferenceAdmin)

