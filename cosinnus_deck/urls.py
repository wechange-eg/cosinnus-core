# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import path, re_path

from cosinnus_deck import views

app_name = 'deck'

cosinnus_root_patterns = [
    path('migrate/todo/<slug:group>/', views.deck_migrate_todo_view, name='deck-migrate-todo'),
]

cosinnus_group_patterns = [
    re_path(r'^$', views.deck_view, name='index'),
]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
