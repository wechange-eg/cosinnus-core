# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django.conf import settings

from cosinnus.forms.profile import UserProfileForm
from cosinnus.models.profile import get_user_profile_model
from cosinnus.views.mixins.avatar import AvatarFormMixin
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError,\
    PermissionDenied
from django.http.response import Http404, HttpResponseRedirect
from cosinnus.models.tagged import BaseTagObject, get_tag_object_model
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership,\
    CosinnusPortal
from cosinnus.models.widget import WidgetConfig
from django.contrib.auth import logout
from cosinnus.utils.permissions import check_user_integrated_portal_member,\
    check_user_can_see_user, check_user_superuser
from django.views.generic.edit import DeleteView
from cosinnus.core.decorators.views import redirect_to_not_logged_in
from cosinnus.utils.urls import safe_redirect
from cosinnus.templatetags.cosinnus_tags import cosinnus_setting
from uuid import uuid1
from cosinnus.views.user import set_user_email_to_verify
from cosinnus.core import signals
from django.forms.fields import CharField
from django.utils.timezone import now
from datetime import timedelta


def deactivate_user(user):
    """ Deactivates a user account """
    user.is_active = False
    user.save()
    # save the user's profile as well, 
    # as numerous triggers occur on the profile instead of the user object
    if user.cosinnus_profile:
        user.cosinnus_profile.save()

 
def deactivate_user_and_mark_for_deletion(user, triggered_by_self=False):
    """ Deacitvates a user account and marks them for deletion in 30 days """
    if user.cosinnus_profile:
        # add a marked-for-deletion flag and a cronjob, deleting the profile using this
        deletion_schedule_time = now() + timedelta(
            days=settings.COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS
        )
        user.cosinnus_profile.scheduled_for_deletion_at = deletion_schedule_time
        user.cosinnus_profile.deletion_triggered_by_self = triggered_by_self
        user.cosinnus_profile.save()
    deactivate_user(user)


def reactivate_user(user):
    """ Reactivates a user account and deletes their marked-for-deletion-flag """
    user.is_active = True
    user.save()
    # save the user's profile as well, 
    # as numerous triggers occur on the profile instead of the user object
    if user.cosinnus_profile:
        # delete the marked-for-deletion flag
        user.cosinnus_profile.scheduled_for_deletion_at = None
        user.cosinnus_profile.deletion_triggered_by_self = False
        user.cosinnus_profile.save()
    else:
        # create a new userprofile if the old one was already deleted, 
        # so we have a functioning user account again
        get_user_profile_model()._default_manager.get_for_user(user)


def delete_userprofile(user):
    """ Deactivate and completely anonymize a user's profile, name and email,
        leaving only the empty User object.
        All content created by the user and foreign-key relations are preserved,
        but will display ""Deleted User)" as creator. """
    
    profile = user.cosinnus_profile
    
    # send deletion signal
    signals.pre_userprofile_delete.send(sender=None, profile=profile)
    
    # delete user widgets
    widgets = WidgetConfig.objects.filter(user_id__exact=user.pk)
    for widget in widgets:
        widget.delete()
    
    # leave all groups
    for membership in CosinnusGroupMembership.objects.filter(user=user):
        membership.delete()
    
    # delete user media_tag
    try:
        if profile.media_tag:
            profile.media_tag.delete()
    except get_tag_object_model().DoesNotExist:
        pass
    
    # delete user profile
    if profile.avatar:
        profile.avatar.delete(False)
    profile.delete()
    
    # set user to inactive and anonymize all data. retain a padded version of his email
    user.first_name = "deleted"
    user.last_name = "user"
    user.username = user.id
    
    # retain email with prefix, cut prefix so field length doesn't break constraints
    scrambled_email_prefix = '__deleted_user__%s' % str(uuid1())[:8]
    scramble_cutoff = user._meta.get_field('email').max_length - len(scrambled_email_prefix) - 2
    scrambled_email_prefix = scrambled_email_prefix[:scramble_cutoff]
    user.email = '%s__%s' % (scrambled_email_prefix, user.email)

    if settings.COSINNUS_IS_OAUTH_CLIENT:
        from allauth.socialaccount.models import SocialAccount
        from allauth.account.models import EmailAddress
        SocialAccount.objects.filter(user=user).delete()
        EmailAddress.objects.filter(user=user).delete()
    
    user.is_active = False
    user.save()


class UserProfileObjectMixin(SingleObjectMixin):
    model = get_user_profile_model()
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_object(self, queryset=None):
        """ Return the userprofile for the current logged in user if no kwarg slug is given,
            or the userprofile for the username slug given """
        
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        
        # return the current user's userprofile if no slug is given
        if not pk and not slug:
            if not self.request.user.is_authenticated:
                return None
            return self.model._default_manager.get_for_user(self.request.user)
        
        if queryset is None:
            queryset = self.get_queryset()
        if pk is not None:
            queryset = queryset.filter(user__pk=pk)
        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{'user__' + slug_field: slug})
        # If none of those are defined, it's an error.
        else:
            raise AttributeError("Generic detail view %s must be called with "
                                 "either an object pk or a slug."
                                 % self.__class__.__name__)
        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except ObjectDoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        
        return obj


class UserProfileDetailView(UserProfileObjectMixin, DetailView):
    template_name = 'cosinnus/user/userprofile_detail.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.request = request
        
        """ Check if the user can access the targeted user profile. """
        target_user_profile = self.get_object(self.get_queryset())
        if not target_user_profile:
            return redirect_to_not_logged_in(request)
        target_user_visibility = target_user_profile.media_tag.visibility
        user = request.user
        # VISIBILITY_ALL users can always be seen, so skip the check
        if not target_user_visibility == BaseTagObject.VISIBILITY_ALL:
            # all other views require at least to be logged in
            if not user.is_authenticated:
                return redirect_to_not_logged_in(request)
            if not check_user_can_see_user(user, target_user_profile.user):
                raise PermissionDenied
            
        return super(UserProfileDetailView, self).dispatch(
            request, *args, **kwargs)
    
    def get_queryset(self):
        if not getattr(self, 'qs', None):
            qs = super(UserProfileDetailView, self).get_queryset()
            if not (self.request.GET.get('force_show', False) == '1' and check_user_superuser(self.request.user)):
                qs = qs.exclude(user__is_active=False).\
                        exclude(user__last_login__exact=None).\
                        filter(settings__contains='tos_accepted')
            self.qs = qs
        return self.qs
    
    def get_context_data(self, **kwargs):
        context = super(UserProfileDetailView, self).get_context_data(**kwargs)
        profile = context['object']
        context.update({
            'optional_fields': profile.get_optional_fields(),
            'profile': profile,
            'this_user': profile.user,
        })
        return context

detail_view = UserProfileDetailView.as_view()


class UserProfileUpdateView(AvatarFormMixin, UserProfileObjectMixin, UpdateView):
    form_class = UserProfileForm
    template_name = 'cosinnus/user/userprofile_form.html'
    message_success = _('Your profile was edited successfully.')
    
    # for extending views, changes some behaviour with the mode that an admin is doing direct changes
    # (e.g. no validation for e-mail changes)
    is_admin_elevated_view = False
    
    # if set to True, all fields will always be kept enabled
    # if set to False, disables some fields depending on settings variables
    disable_conditional_field_locking = False
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserProfileObjectMixin, self).dispatch(
            request, *args, **kwargs)
    
    def get_initial(self):
        """ Allow pre-populating managed tags on userprofile edit from initial default tags """
        initial = super().get_initial()
        if settings.COSINNUS_MANAGED_TAGS_ENABLED and \
                (settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF or settings.COSINNUS_MANAGED_TAGS_ASSIGNABLE_IN_USER_ADMIN_FORM):
            if settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG is not None:
                initial['managed_tag_field'] = settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG
        return initial
    
    def get_success_url(self):
        return reverse('cosinnus:profile-detail')
    
    def post(self, request, *args, **kwargs):
        """ if user changed his email, check if user is member of an integrated portal, 
            and if so ignore that change. Also, ignore the change if email verification is active, and instead
            set a new email-to-be-verified and send user a confirmation email. """
        self.object = self.get_object()
        user = self.object.user
        if request.POST.get('user-email', user.email) != user.email and check_user_integrated_portal_member(user):
            messages.warning(request, _('Your user account is associated with an integrated Portal. This account\'s email address is fixed and therefore was left unchanged.'))
            request.POST._mutable = True
            request.POST['user-email'] = user.email
        elif not self.is_admin_elevated_view and request.POST.get('user-email', user.email) != user.email and CosinnusPortal.get_current().email_needs_verification:
            # set flags to be changed if form submit is successful
            self.target_email_to_confirm = request.POST['user-email']
            self.user = user
            request.POST._mutable = True
            request.POST['user-email'] = user.email
        return super(UserProfileUpdateView, self).post(request, *args, **kwargs)
    
    def form_valid(self, form):
        try:
            ret = super(UserProfileUpdateView, self).form_valid(form)
            messages.success(self.request, self.message_success)
            
            # send out email confirmation email
            if getattr(self, 'target_email_to_confirm', None):
                set_user_email_to_verify(self.user, self.target_email_to_confirm, self.request, user_has_just_registered=False)
                messages.warning(self.request, _('You have changed your email address. We will soon send you an email to that address with a confirmation link. Until you click on that link, your profile will retain your old email address!'))
            
        except AttributeError as e:
            if str(e) == "'dict' object has no attribute '_committed'":
                # here we couldn't save the avatar
                messages.error(self.request, _('Sorry, your profile could not be saved because there was an error while processing the avatar!'))
            else:
                messages.error(self.request, _('Sorry, something went wrong while saving your profile!'))
            ret = HttpResponseRedirect(reverse('cosinnus:profile-edit'))
        return ret
    
    def get_form(self, *args, **kwargs):
        form = super(UserProfileUpdateView, self).get_form(*args, **kwargs)
        # note: we have a django-multiforms form here with 'user', 'obj' (CosinnusProfile) and 'media_tag'!
        
        if not self.disable_conditional_field_locking:
            for form_name, formfield_list in settings.COSINNUS_USERPROFILE_DISABLED_FIELDS.items():
                sub_form = form.forms[form_name]
                # disable profile formfields from settings
                # we also need to remove any validation errors from required later-disabled fields
                for field_name in formfield_list:
                    if field_name in sub_form.fields:
                        field = sub_form.fields[field_name]
                        field.disabled = True
                        field.required = False
            # disable the userprofile visibility field if it is locked
            if settings.COSINNUS_USERPROFILE_VISIBILITY_SETTINGS_LOCKED is not None:
                field = form.forms['media_tag'].fields['visibility']
                field.disabled = True
                field.required = False
        
        # disable all fields that require a certain managed_tag to be assigned to the user
        # that this user doesn't have
        user_managed_tag_slugs = [tag.slug for tag in self.object.get_managed_tags()]
        for tag_slug_list, field_list in settings.COSINNUS_USERPROFILE_EXTRA_FIELDS_ONLY_ENABLED_FOR_MANAGED_TAGS:
            if not any([tag_slug in user_managed_tag_slugs for tag_slug in tag_slug_list]):
                for field_name in field_list:
                    if field_name in form.forms['obj'].fields:
                        field = form.forms['obj'].fields[field_name]
                        field.disabled = True
                        field.required = False
        
        return form
    

update_view = UserProfileUpdateView.as_view()


class UserProfileDeleteView(AvatarFormMixin, UserProfileObjectMixin, DeleteView):
    #form_class = UserProfileForm
    template_name = 'cosinnus/user/userprofile_delete.html'
    message_success = _('Your user account has been deactivated and will be deleted in 30 days. We\'re sorry you are no longer with us.')
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserProfileDeleteView, self).dispatch(
            request, *args, **kwargs)

    def get_success_url(self):
        return reverse('login')
    
    def _validate_user_delete_safe(self, user):
        is_safe = user.is_authenticated
        
        for group in CosinnusGroup.objects.get_for_user(user):
            admins = CosinnusGroupMembership.objects.get_admins(group=group)
            if user.pk in admins:
                messages.error(self.request, _('You are the only administrator left for "%(group_name)s". Please appoint a different administrator or delete it first.' % {'group_name': group.name}))
                is_safe = False
        
        return is_safe
    
    def get(self, request, *args, **kwargs):
        self._validate_user_delete_safe(self.request.user)
        return super(UserProfileDeleteView, self).get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self._validate_user_delete_safe(request.user):
            return HttpResponseRedirect(reverse('cosinnus:profile-delete'))
        
        # this no longer immediately deletes the user profile, but instead deactivates it!
        # function after 30 days.
        deactivate_user_and_mark_for_deletion(request.user, triggered_by_self=True)
        
        # log user out
        logout(request)
        
        messages.success(self.request, self.message_success)
        return HttpResponseRedirect(self.get_success_url())
    

delete_view = UserProfileDeleteView.as_view()
