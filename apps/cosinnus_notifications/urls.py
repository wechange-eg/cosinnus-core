# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from cosinnus_notifications import views

app_name = 'notifications'

cosinnus_root_patterns = [
    url(r'^profile/notifications/$', views.notification_preference_view, name='notifications'),
    url(r'^profile/reset_notifications/$', views.notification_reset_view, name='reset-notifications'),
    
    url(r'^profile/api/alerts/get/$', views.alerts_retrieval_view, name='alerts-get'),
    url(r'^profile/api/alerts/get/(?P<newer_than_timestamp>[^/]+)/$', views.alerts_retrieval_view, name='alerts-get-newest'),
    url(r'^profile/api/alerts/markseen/$', views.alerts_mark_seen, name='alerts-mark-seen'),
    url(r'^profile/api/alerts/markseen/(?P<before_timestamp>[^/]+)/$', views.alerts_mark_seen, name='alerts-mark-seen-before'),
]

cosinnus_group_patterns = []


urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
