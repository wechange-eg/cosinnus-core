# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import path, re_path

from cosinnus.conf import settings
from cosinnus_deck import views

app_name = 'deck'

cosinnus_root_patterns = []

if settings.COSINNUS_DECK_MIGRATE_USER_DECKS:
    cosinnus_root_patterns += [
        path('migrate/user_decks/', views.deck_migrate_user_decks_view, name='deck-migrate-user-decks'),
        path('migrate/user_decks/api/', views.deck_migrate_user_decks_api_view, name='deck-migrate-user-decks-api'),
    ]

cosinnus_group_patterns = [
    re_path(r'^$', views.deck_view, name='index'),
    re_path('^migrate/todos/$', views.deck_migrate_todo_view, name='migrate-todos'),
]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
