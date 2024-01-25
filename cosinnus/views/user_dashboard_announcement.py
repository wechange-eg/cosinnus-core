from __future__ import unicode_literals

from builtins import object
import logging

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, UpdateView

from cosinnus.models.group import CosinnusPortal
from django.urls import reverse
from cosinnus.forms.user_dashboard_announcement import UserDashboardAnnouncementForm
from cosinnus.models.user_dashboard_announcement import UserDashboardAnnouncement
from cosinnus.views.mixins.group import RequireSuperuserMixin
from django.views.generic.list import ListView
from cosinnus.utils.permissions import check_user_superuser
from django.http.response import HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import redirect
from annoying.functions import get_object_or_None


logger = logging.getLogger('cosinnus')


class SamePortalGroupMixin(object):

    def get_queryset(self):
        """
        Filter the queryset for this portal only!
        """
        return super(SamePortalGroupMixin, self).get_queryset().filter(portal=CosinnusPortal.get_current())


class UserDashboardAnnouncementFormMixin(object):
    
    form_class = UserDashboardAnnouncementForm
    model = UserDashboardAnnouncement
    template_name = 'cosinnus/user_dashboard_announcement/user_dashboard_announcement_form.html'
    
    
class UserDashboardAnnouncementListView(RequireSuperuserMixin, SamePortalGroupMixin, ListView):

    model = UserDashboardAnnouncement
    template_name = 'cosinnus/user_dashboard_announcement/user_dashboard_announcement_list.html'
    
    def get_context_data(self, **kwargs):
        context = super(UserDashboardAnnouncementListView, self).get_context_data(**kwargs)
        context.update({
        })
        return context

list_view = UserDashboardAnnouncementListView.as_view()


class UserDashboardAnnouncementCreateView(RequireSuperuserMixin, SamePortalGroupMixin, UserDashboardAnnouncementFormMixin, CreateView):
    """ Create View for UserDashboardAnnouncements """
    
    form_view = 'add'
    message_success = _('Your Announcement was created successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(UserDashboardAnnouncementCreateView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context
    
    def form_valid(self, form):
        form.instance.creator = self.request.user
        ret = super(UserDashboardAnnouncementCreateView, self).form_valid(form)
        return ret
    
    def get_success_url(self):
        messages.success(self.request, self.message_success)
        return self.object.get_edit_url()
    
user_dashboard_announcement_create = UserDashboardAnnouncementCreateView.as_view()


class UserDashboardAnnouncementEditView(RequireSuperuserMixin, SamePortalGroupMixin, UserDashboardAnnouncementFormMixin, UpdateView):

    form_view = 'edit'
    message_success = _('Your Announcement was saved successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(UserDashboardAnnouncementEditView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        messages.success(self.request, self.message_success)
        return self.object.get_edit_url()
    

user_dashboard_announcement_edit = UserDashboardAnnouncementEditView.as_view()


class UserDashboardAnnouncementDeleteView(RequireSuperuserMixin, SamePortalGroupMixin, DeleteView):

    model = UserDashboardAnnouncement
    message_success = _('Your Announcement was deleted successfully.')
    
    def get_success_url(self):
        messages.success(self.request, self.message_success)
        return reverse('cosinnus:user-dashboard-announcement-list')

user_dashboard_announcement_delete = UserDashboardAnnouncementDeleteView.as_view()


def user_dashboard_announcement_activate(request, slug):
    """ Toggles an announcement active/inactive """
    if not check_user_superuser(request.user):
        return HttpResponseForbidden('Not authenticated')
    
    announcement = get_object_or_None(UserDashboardAnnouncement, portal=CosinnusPortal.get_current(), slug=slug)
    if announcement is None:
        return HttpResponseNotFound()
    announcement.is_active = not announcement.is_active
    announcement.save()
    if announcement.is_active:
        messages.success(request, _('Your Announcement was activated successfully.'))
    else:
        messages.success(request, _('Your Announcement was deactivated successfully.'))
    return redirect('cosinnus:user-dashboard-announcement-list')
    