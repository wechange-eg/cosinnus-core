# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import FormView

from cosinnus.conf import settings
from cosinnus.forms.mitwirkomat import MitwirkomatSettingsAnswerFormSet, MitwirkomatSettingsForm
from cosinnus.models.mitwirkomat import MitwirkomatSettings
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.views.group import SamePortalGroupMixin
from cosinnus.views.mixins.avatar import AvatarFormMixin
from cosinnus.views.mixins.formsets import JsonFieldFormsetMixin
from cosinnus.views.mixins.group import (
    DipatchGroupURLMixin,
    RequireAdminMixin,
    RequireExtraDispatchCheckMixin,
)

logger = logging.getLogger('cosinnus')


class MitwirkomatSettingsView(
    SamePortalGroupMixin,
    RequireAdminMixin,
    AvatarFormMixin,
    DipatchGroupURLMixin,
    RequireExtraDispatchCheckMixin,
    JsonFieldFormsetMixin,
    FormView,
):
    """This view combines create and edit view, since the Mitwirkomat Settings object is an optional one-to-one rel
    to its group. On deactivation of the Mitwirkomat integration for a group, we only set `is_active` to false, but
    never delete a settings object."""

    form_class = MitwirkomatSettingsForm
    template_name = 'cosinnus/mitwirkomat/mitwirkomat_settings_form.html'

    json_field_formsets = {
        'questions': MitwirkomatSettingsAnswerFormSet,
    }

    def extra_dispatch_check(self):
        if self.group.type not in settings.COSINNUS_MITWIRKOMAT_ENABLED_FOR_GROUP_TYPES:
            messages.error(self.request, _('This function is not enabled for this group type.'))
            return redirect(group_aware_reverse('cosinnus:group-dashboard', kwargs={'group': self.group}))

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        if self.get_instance():
            form_kwargs['instance'] = self.get_instance()
        return form_kwargs

    def get_instance(self):
        return getattr(self.group, 'mitwirkomat_settings', None)

    def json_field_formset_initial(self):
        return {
            'questions': [
                {'question': key, 'answer': settings.COSINNUS_MITWIRKOMAT_QUESTION_DEFAULT_VALUE}
                for key in settings.COSINNUS_MITWIRKOMAT_QUESTION_LABELS.keys()
            ]
        }

    def form_valid(self, form):
        """This is the custom form_valid as required by `JsonFieldFormsetMixin`."""
        json_field_formsets_valid = self.json_field_formset_form_valid_hook()
        if not json_field_formsets_valid:
            return self.render_to_response(self.get_context_data(form=form))

        # Manual `AvatarFormMixin` integration, since we do not call `super().form_valid()` here to trigger it.
        self._save_awesome_avatar(form)

        if not form.instance.id:
            instance = form.save(commit=False)
            instance.group = self.group
            instance.creator = self.request.user
            self.json_field_formset_pre_save_hook(instance)
            instance.save()
        else:
            instance = form.save()
            self.json_field_formset_pre_save_hook(instance)
            instance.save()
        messages.success(self.request, _('Your Matching Settings for the Volunteer-O-Matic have been saved.'))

        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'group': self.group,
                'object': self.get_instance(),
                'mitwirkomat_question_choices': MitwirkomatSettings.QUESTION_CHOICES,
            }
        )
        return context

    def get_success_url(self):
        return '.'  # redirects to same form


mitwirkomat_settings_view = MitwirkomatSettingsView.as_view()
