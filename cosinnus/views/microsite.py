# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.http.response import Http404, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from cosinnus.conf import settings
from cosinnus.core.decorators.views import redirect_to_not_logged_in
from cosinnus.core.mail import send_html_mail_threaded
from cosinnus.forms.group import GroupContactForm
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.views.mixins.group import DipatchGroupURLMixin, GroupObjectCountMixin
from cosinnus.views.mixins.tagged import DisplayTaggedObjectsMixin


class GroupMicrositeView(DipatchGroupURLMixin, GroupObjectCountMixin, DisplayTaggedObjectsMixin, TemplateView):
    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, 'COSINNUS_MICROSITES_ENABLED', False):
            raise Http404
        # if microsite access is limited, only allow invite-links, but nothing else
        if (
            not self.request.user.is_authenticated
            and getattr(settings, 'COSINNUS_MICROSITES_DISABLE_ANONYMOUS_ACCESS', False)
            and not request.GET.get('invited', None) == '1'
        ):
            return redirect_to_not_logged_in(self.request, view=self)
        ret = super(GroupMicrositeView, self).dispatch(request, *args, **kwargs)

        # check if microsite/group is really publicly accesible; if not, redirect after all
        if not self.request.user.is_authenticated and not self.group.is_publicly_visible:
            return redirect_to_not_logged_in(self.request, group=self.group)
        return ret

    def get_template_names(self):
        """Return the extending compact-conference microsite if this is a conference
        and conferences are shown in compact mode"""
        if self.group.group_is_conference:
            return ['cosinnus/group/conference_compact_microsite.html']
        return ['cosinnus/group/group_microsite.html']

    def get_public_objects(self):
        """Returns a list of tuples [('<app>', <app_name>'m [<app_items>]), ...]"""
        querysets = self.get_object_querysets(group=self.group, cosinnus_apps=self.group.get_microsite_public_apps())

        public_object_list = defaultdict(list)
        for queryset in querysets:
            items = self.sort_and_limit_single_queryset(
                queryset, item_limit=settings.COSINNUS_MICROSITE_PUBLIC_APPS_NUMBER_OF_ITEMS
            )
            if items:
                public_object_list[items[0].get_cosinnus_app_name()].extend(items)
        public_objects = []
        for app_name, items in public_object_list.items():
            public_objects.append((items[0].get_cosinnus_app(), app_name, items))
        return public_objects

    def send_message_to_group_admins(self, **kwargs):
        group_admins = self.group.actual_admins
        subject = render_to_string('cosinnus/mail/message_from_contact_form_subj.txt', kwargs)
        text = textfield(render_to_string('cosinnus/mail/message_from_contact_form.html', kwargs))
        for admin in group_admins:
            send_html_mail_threaded(admin, subject, text, ' ')
        pass

    def post(self, request, group=None):
        if settings.COSINNUS_ALLOW_CONTACT_FORM_ON_MICROPAGE:
            contact_form = GroupContactForm(data=request.POST)
            if contact_form.is_valid():
                message = contact_form.cleaned_data.get('message')
                email = contact_form.cleaned_data.get('email')
                self.send_message_to_group_admins(
                    message=message, email=email, group_name=self.group.name, group_url=self.group.get_absolute_url()
                )
                messages.add_message(request, messages.SUCCESS, _('Your message has been sent.'))
                return HttpResponseRedirect(request.path_info)
            else:
                messages.add_message(
                    request, messages.ERROR, _('Something went wrong. ' + 'Your message was not sent.')
                )
                context = self.get_context_data(contact_form=contact_form)
                return self.render_to_response(context)
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(GroupMicrositeView, self).get_context_data(**kwargs)
        context.update(
            {
                'public_objects': self.get_public_objects(),
                'anonymous_user': AnonymousUser(),
            }
        )
        if (
            settings.COSINNUS_ALLOW_CONTACT_FORM_ON_MICROPAGE
            and self.group.show_contact_form
            and 'contact_form' not in kwargs
        ):
            context.update({'contact_form': GroupContactForm()})
        return context


group_microsite_view = GroupMicrositeView.as_view()

# this view is only called from within the group-startpage redirect view
