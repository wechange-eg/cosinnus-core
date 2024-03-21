# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import path
from cosinnus_notifications import views

app_name = 'notifications'

cosinnus_root_patterns = [
    path('profile/notifications/', views.notification_preference_view, name='notifications'),
    path('profile/reset_notifications/', views.notification_reset_view, name='reset-notifications'),
    
    path('profile/api/alerts/get/', views.alerts_retrieval_view, name='alerts-get'),
    path('profile/api/alerts/get/<str:newer_than_timestamp>/', views.alerts_retrieval_view, name='alerts-get-newest'),
    path('profile/api/alerts/markseen/', views.alerts_mark_seen, name='alerts-mark-seen'),
    path('profile/api/alerts/markseen/<str:before_timestamp>/', views.alerts_mark_seen, name='alerts-mark-seen-before'),
]

cosinnus_group_patterns = []


urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
