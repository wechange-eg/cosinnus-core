from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DeleteView, DetailView
from extra_views import CreateWithInlinesView, UpdateWithInlinesView

from ajax_forms.ajax_forms import AjaxFormsDeleteViewMixin
from cosinnus import cosinnus_notifications
from cosinnus.forms.mixins import AdditionalFormsMixin
from cosinnus.models import MEMBERSHIP_ADMIN
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.views.group import SamePortalGroupMixin
from cosinnus.views.mixins.avatar import AvatarFormMixin
from cosinnus.views.mixins.group import RequireLoggedInMixin, RequireWriteGrouplessMixin
from cosinnus_organization.forms import CosinnusOrganizationForm, CosinnusOrganizationLocationInlineFormset, \
    CosinnusOrganizationSocialMediaInlineFormset
from cosinnus_organization.models import CosinnusOrganization, CosinnusOrganizationMembership


class OrganizationDetailView(DetailView):
    model = CosinnusOrganization
    slug_url_kwarg = 'organization'

    def get(self, request, *args, **kwargs):
        return redirect(reverse('cosinnus:map') + f'?item=1.organizations.{self.get_object().slug}')


class CosinnusOrganizationFormMixin(object):
    form_class = CosinnusOrganizationForm
    model = CosinnusOrganization
    template_name = 'cosinnus/organization/organization_form.html'

    inlines = [CosinnusOrganizationLocationInlineFormset, CosinnusOrganizationSocialMediaInlineFormset]

    def get_form_kwargs(self):
        kwargs = super(CosinnusOrganizationFormMixin, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def dispatch(self, *args, **kwargs):
        """ Find out which type of CosinnusOrganization (project/society), we're dealing with here. """
        # special check, if group/project creation is limited to admins, deny regular users creating groups/projects
        if getattr(settings, 'COSINNUS_LIMIT_ORGANIZATION_CREATION_TO_ADMINS', False) \
                and not check_user_superuser(self.request.user) and self.form_view == 'add':
            messages.warning(self.request, _('Sorry, only portal administrators can create projects and groups!'))
            return redirect(reverse('cosinnus:portal-admin-list'))

        # special check: only portal admins can create groups
        if not getattr(settings, 'COSINNUS_USERS_CAN_CREATE_ORGANIZATIONS', False) \
                and self.form_view == 'add':
            if not check_user_superuser(self.request.user):

                if getattr(settings, 'COSINNUS_CUSTOM_PREMIUM_PAGE_ENABLED', False):
                    redirect_url = reverse('cosinnus:premium-info-page')
                else:
                    messages.warning(self.request, _(
                        'Sorry, only portal administrators can create Organizations! You can either create a Project, or write a message to one of the administrators to create a Organization for you. Below you can find a listing of all administrators.'))
                    redirect_url = reverse('cosinnus:portal-admin-list')
                return redirect(redirect_url)

        return super(CosinnusOrganizationFormMixin, self).dispatch(*args, **kwargs)

    def forms_valid(self, form, inlines):
        if form.instance.pk is None:
            form.instance.creator = self.request.user
        ret = super(CosinnusOrganizationFormMixin, self).forms_valid(form, inlines)
        self.object.update_index()
        return ret


class OrganizationCreateView(RequireLoggedInMixin, CosinnusOrganizationFormMixin, AvatarFormMixin,
                             AdditionalFormsMixin, CreateWithInlinesView):
    """ Create View for Organizations """

    form_view = 'add'
    slug_url_kwarg = 'organization'
    message_success = _('Organization "%(name)s" was created successfully.')

    def get_context_data(self, **kwargs):
        context = super(OrganizationCreateView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        # Forward to next additional form
        if len(self.extra_forms) > 0:
            tab = self.request.GET.get('tab', 0)
            if tab < len(self.extra_forms):
                return reverse('cosinnus:organization-edit', kwargs={'organization': self.object.slug}) + f"./?tab={tab + 1}"
        return self.object.get_absolute_url() + '&action=create'

    def forms_valid(self, form, inlines):
        ret = super(OrganizationCreateView, self).forms_valid(form, inlines)
        membership = CosinnusOrganizationMembership.objects.create(user=self.request.user,
                                                                   group=self.object, status=MEMBERSHIP_ADMIN)

        # clear cache and manually refill because race conditions can make the group memberships be cached as empty
        membership._clear_cache()
        self.object.members  # this refills the group's member cache immediately
        self.object.admins  # this refills the group's member cache immediately

        cosinnus_notifications.organization_created.send(sender=self, user=self.request.user, obj=self.object,
                                                         audience=[])
        messages.success(self.request, self.message_success % {'name': self.object.name})
        return ret


class OrganizationEditView(RequireWriteGrouplessMixin, AvatarFormMixin, CosinnusOrganizationFormMixin,
                           AdditionalFormsMixin, UpdateWithInlinesView):
    form_view = 'edit'
    slug_url_kwarg = 'organization'

    def get_context_data(self, **kwargs):
        context = super(OrganizationEditView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        return self.object.get_absolute_url() + '&action=edit'


class OrganizationDeleteView(RequireWriteGrouplessMixin, SamePortalGroupMixin, AjaxFormsDeleteViewMixin,
                             DeleteView):
    model = CosinnusOrganization
    slug_url_kwarg = 'organization'
    message_success = _('Your organization was deleted successfully.')

    def get_success_url(self):
        # disabled the success message for now as it isn't displayed on the map
        # messages.success(self.request, self.message_success)
        return reverse('cosinnus:organization-list-mine')


organization_detail = OrganizationDetailView.as_view()
organization_create = OrganizationCreateView.as_view()
organization_edit = OrganizationEditView.as_view()
organization_delete = OrganizationDeleteView.as_view()