# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from cosinnus_notifications.models import NotificationAlert, NotificationEvent, UserNotificationPreference


class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'notification_id', 'setting')
    list_filter = ('setting',)
    search_fields = (
        'user__first_name',
        'user__last_name',
        'user__email',
        'notification_id',
        'group__name',
        'group__slug',
    )


admin.site.register(UserNotificationPreference, UserNotificationPreferenceAdmin)


class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ('date', 'notification_id', 'group', 'user')
    list_filter = ('notification_id',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'notification_id', 'group__name')


admin.site.register(NotificationEvent, NotificationEventAdmin)


class NotificationAlertAdmin(admin.ModelAdmin):
    list_display = ('last_event_at', 'type', 'notification_id', 'group', 'user', 'action_user')
    list_filter = (
        'notification_id',
        'portal',
    )
    search_fields = (
        'user__first_name',
        'user__last_name',
        'user__email',
        'action_user__first_name',
        'action_user__last_name',
        'action_user__email',
        'notification_id',
        'group__name',
    )
    readonly_fields = ('type',)


admin.site.register(NotificationAlert, NotificationAlertAdmin)
