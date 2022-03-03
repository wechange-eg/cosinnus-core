# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from cosinnus_marketplace import views

app_name = 'marketplace'

cosinnus_group_patterns = [
    url(r'^$', views.index_view, name='index'),

    url(r'^list/$', views.offer_list_view, name='list', kwargs={'offer_view': 'all'}),
    url(r'^list/mine/$', views.offer_list_view, name='list_mine', kwargs={'offer_view': 'mine'}),
    url(r'^list/delete_element/$', views.delete_element_view, name='delete-element'),
    
    
    url(r'^add/$', views.offer_add_view,  {'form_view': 'add'},  name='add'),
    url(r'^(?P<slug>[^/]+)/$', views.offer_detail_view, {'form_view': 'edit'},  name='detail'),
    url(r'^(?P<slug>[^/]+)/edit/$', views.offer_edit_view, {'form_view': 'edit'}, name='edit'),
    url(r'^(?P<slug>[^/]+)/delete/$', views.offer_delete_view, {'form_view': 'delete'}, name='delete'),
    url(r'^(?P<slug>[^/]+)/activate/$', views.offer_activate_or_deactivate_view, {'mode': 'activate'}, name='activate'),
    url(r'^(?P<slug>[^/]+)/deactivate/$', views.offer_activate_or_deactivate_view, {'mode': 'deactivate'}, name='deactivate'),
    
    
    url(r'^(?P<offer_slug>[^/]+)/comment/$', views.comment_create, name='comment'),
    url(r'^comment/(?P<pk>\d+)/$', views.comment_detail, name='comment-detail'),
    url(r'^comment/(?P<pk>\d+)/delete/$', views.comment_delete, name='comment-delete'),
    url(r'^comment/(?P<pk>\d+)/update/$', views.comment_update, name='comment-update'),
]


cosinnus_root_patterns = []
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
