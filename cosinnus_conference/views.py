# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.generic import TemplateView

from cosinnus.models.group_extra import CosinnusSociety


@login_required
def conference_redirect(request):
    response = redirect('/conference/lobby/')
    return response


class Conference(TemplateView):
    """Conference base view"""
    template_name = 'conference/index.html'
    view = ''

    def __init__(self, *args, **kwargs):
        self.view = kwargs.pop('view')
        super().__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(Conference, self).get_context_data(**kwargs)
        context['group'] = CosinnusSociety.objects.get(id=3)
        context['view'] = self.view
        return context


conference_lobby = login_required(Conference.as_view(view='lobby'))
conference_stage = login_required(Conference.as_view(view='stage'))
conference_discussions = login_required(Conference.as_view(view='discussions'))
conference_workshops = login_required(Conference.as_view(view='workshops'))
conference_coffee_tables = login_required(Conference.as_view(view='coffee-tables'))
conference_networking = login_required(Conference.as_view(view='networking'))
conference_exhibition = login_required(Conference.as_view(view='exhibition'))
