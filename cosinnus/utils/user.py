# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from cosinnus.conf import settings
from cosinnus.core.registries.widgets import widget_registry
from cosinnus.utils.group import get_cosinnus_group_model,\
    get_default_user_group_slugs
from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned
from django.utils.crypto import get_random_string
from django.db.models import Q
import six
from django.template.loader import render_to_string
from django.utils.html import escape
from django.apps import apps
from django.urls import reverse
from cosinnus.utils.urls import get_domain_for_portal
from cosinnus.utils.tokens import email_blacklist_token_generator
from django.utils.timezone import now, is_naive
from dateutil import parser
import datetime
import pytz


_CosinnusPortal = None

logger = logging.getLogger('cosinnus')


def get_user_by_email_safe(email):
    """ Gets a user by email from the DB. Works around the fact that we're using a non-unique email
        field, but assume it should be unique.
        
        This method DOES NOT throw USER_MODEL.DoesNotExist! If no user was found, it returns None instead!
        
        If a user with the same 2 (case-insensitive) email addresses is found, we:
            - keep the user with the most recent login date and lowercase his email-address
            - set the older users inactive and change their email to '__deduplicate__<old-email>'
            
        @return: None if no user was found. A user object if found, even if it had a duplicated email.
    """
    USER_MODEL = get_user_model()
    if not email:
        return None
    try:
        user = USER_MODEL.objects.get(email__iexact=email)
        return user
    except MultipleObjectsReturned:
        users = USER_MODEL.objects.filter(email__iexact=email)
        # if none of the users has logged in, take the newest registered
        if users.filter(last_login__isnull=False).count() == 1:
            newest = users.latest('date_joined')
        elif users.filter(last_login__isnull=False).count() == 0:
            newest = users[0]
        else:
            newest = users.filter(last_login__isnull=False).latest('last_login')
        others = users.exclude(id=newest.id)
        
        newest.email = newest.email.lower()
        newest.save()
        
        for user in others:
            user.is_active = False
            user.email = '__deduplicate__%s' % user.email
            user.save()
            
        # we re-retrieve the newest user here so we can fail early here if something went really wrong
        return USER_MODEL.objects.get(email__iexact=email)
    
    except USER_MODEL.DoesNotExist:
        return None
        
        
def ensure_user_widget(user, app_name, widget_name, config={}):
    """ Makes sure if a widget exists for the given user, and if not, creates it """
    from cosinnus.models.widget import WidgetConfig
    wqs = WidgetConfig.objects.filter(user_id=user.pk, app_name=app_name, widget_name=widget_name)
    if wqs.count() <= 0:
        widget_class = widget_registry.get(app_name, widget_name)
        widget = widget_class.create(None, group=None, user=user)
        widget.save_config(config)

    
def assign_user_to_default_auth_group(sender, **kwargs):
    from django.contrib.auth.models import Group
    user = kwargs.get('instance')
    for group_name in getattr(settings, 'NEWW_DEFAULT_USER_AUTH_GROUPS', []):
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue
        group.user_set.add(user)
        
def ensure_user_to_default_portal_groups(sender, created, **kwargs):
    """ Whenever a portal membership changes, make sure the user is in the default groups for this Portal """
    try:
        from cosinnus.models.group import CosinnusGroupMembership
        from cosinnus.models.membership import MEMBERSHIP_MEMBER
        membership = kwargs.get('instance')
        CosinnusGroup = get_cosinnus_group_model()
        for group_slug in get_default_user_group_slugs():
            try:
                group = CosinnusGroup.objects.get(slug=group_slug, portal_id=membership.group.id)
                CosinnusGroupMembership.objects.get_or_create(user=membership.user, group=group, defaults={'status': MEMBERSHIP_MEMBER})
            except CosinnusGroup.DoesNotExist:
                continue
            
    except:
        # We fail silently, because we never want to 500 here unexpectedly
        logger.error("Error while trying to add User Membership for newly created user.")

def filter_active_users(user_model_qs, filter_on_user_profile_model=False):
    """ Filters a QS of ``get_user_model()`` so that all users are removed that are either of
            - inactive
            - have never logged in
            - have not accepted the ToS 
        @param filter_on_user_profile_model: Filter not on User, but on CosinnusUserProfile instead """
    if filter_on_user_profile_model:
        return user_model_qs.exclude(user__is_active=False).\
            exclude(user__last_login__exact=None).\
            filter(settings__contains='tos_accepted')
    else:
        return user_model_qs.exclude(is_active=False).\
            exclude(last_login__exact=None).\
            filter(cosinnus_profile__settings__contains='tos_accepted')
            
def filter_portal_users(user_model_qs, portal=None):
    """ Filters a QS of ``get_user_model()`` so that only users of this portal remain. """
    if portal is None:
        global _CosinnusPortal
        if _CosinnusPortal is None: 
            _CosinnusPortal = apps.get_model('cosinnus', 'CosinnusPortal')
        portal = _CosinnusPortal.get_current()
    return user_model_qs.filter(id__in=portal.members)


def get_user_query_filter_for_search_terms(terms):
    """ Returns a django Q filter for use on USER_MODEL that returns all users with matching
        names, given an array of search terms. Each search term needs to be matched (AND)
        on at least one of the user's name fields (OR). Case is insensitive.
        User name fields are USER_MODEL.first_name, USER_MODEL.last_name, as well as any
        additional fields defined in the user profile model (``ADDITIONAL_USERNAME_FIELDS``).
        @param terms: An array of string search terms.
        @return: A django Q object.
    """
    from cosinnus.models.profile import get_user_profile_model
    ADDITIONAL_USERNAME_FIELDS = get_user_profile_model().ADDITIONAL_USERNAME_FIELDS
    first_term, other_terms = terms[0], terms[1:]

    # username is not used as filter for the term for now, might confuse
    # users why a search result is found
    q = Q(first_name__icontains=first_term) | Q(last_name__icontains=first_term) 
    for field_name in ADDITIONAL_USERNAME_FIELDS:
        q |= Q(**{'cosinnus_profile__%s__icontains' % field_name: first_term})
    for other_term in other_terms:
        add_q = Q(first_name__icontains=other_term) | Q(last_name__icontains=other_term)
        for field_name in ADDITIONAL_USERNAME_FIELDS:
            add_q |= Q(**{'cosinnus_profile__%s__icontains' % field_name: first_term})
        q &= add_q
        
    return q
        

# very similar to create_user but uses UserCreateForm from django.contrib.auth as the one from cosinnus.forms.user requires a captcha
def create_base_user(email, username=None, password=None, first_name=None, last_name=None, no_generated_password=False):
    """ :param no_generated_password: set password generation behaviour. If False Password will be kept with None
        :type no_generated_password: bool | default False
    """

    from django.contrib.auth.forms import UserCreationForm
    from cosinnus.models.profile import get_user_profile_model
    from cosinnus.models.group import CosinnusPortalMembership, CosinnusPortal
    from cosinnus.models.membership import MEMBERSHIP_MEMBER
    from cosinnus.views.user import email_first_login_token_to_user
    from django.contrib.auth import get_user_model
    from django.core.exceptions import ObjectDoesNotExist

    try:
        user_model = get_user_model()
        user_model.objects.get(email__iexact=email)
        logger.warning('Manual user creation failed because email already exists!')
        return False
    except ObjectDoesNotExist:
        pass

    if not password and no_generated_password:
        # special handling for user without password
        user_model = get_user_model()
        temp_username = email if not username else username

        # check if user with that password already exist
        user, created = user_model.objects.get_or_create(username=temp_username, email=email)

        email_first_login_token_to_user(user=user)
        if not created:
            logger.error('Manual user creation failed. A user with tha username already exists!')

    else:
        password = get_random_string()

        user_data = {
            'username': username or get_random_string(),
            'password1': password,
            'password2': password
        }

        form = UserCreationForm(user_data)
        if form.is_valid():
            user = form.save()
        else:
            logger.warning('Manual user creation failed because of form errors!', extra={'data': user_data, 'form-errors': form.errors})
            return False

    user.email = email
    if not username:
        user.username = user.id
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    user.backend = 'cosinnus.backends.EmailAuthBackend'
    user.save()

    CosinnusPortalMembership.objects.get_or_create(group=CosinnusPortal.get_current(),
                                                   user=user, defaults={'status': MEMBERSHIP_MEMBER})

    profile = get_user_profile_model()._default_manager.get_for_user(user)
    profile.settings['tos_accepted'] = False
    profile.save()

    return user


def create_user(email, username=None, first_name=None, last_name=None, tos_checked=True):
    """ Creates a user with a random password, and adds proper PortalMemberships for this portal.
        @param email: Email is required because it's basically our pk
        @param username: Can be left blank and will then be set to the user's id after creation.
        @param tos_checked: Set to False if the user should have to check the Terms of Services upon first login.
        @return: A <USER_MODEL> instance if creation successful, False if failed to create (was the username taken?)
    """
    from cosinnus.forms.user import UserCreationForm
    from cosinnus.models.profile import get_user_profile_model # leave here because of cyclic imports
    
    pwd = get_random_string()
    data = {
        'username': username or get_random_string(),
        'email': email,
        'password1': pwd,
        'password2': pwd,
        'first_name': first_name,
        'last_name': last_name,
        'tos_check': True, # needs to be True for form validation, may be reset later
    }
    # use Cosinnus' UserCreationForm to apply all usual user-creation-related effects
    form = UserCreationForm(data)
    if form.is_valid():
        user = form.save()
    else:
        logger.warning('Manual user creation failed because of form errors!', extra={'data': data, 'form-errors': form.errors})
        return False
    # always retrieve this to make sure the profile was created, we had a Heisenbug here
    profile = get_user_profile_model()._default_manager.get_for_user(user)
    
    if not tos_checked:
        profile.settings['tos_accepted'] = False
        profile.save()
    
    # username is always its id
    user.username = user.id
    
    user.backend = 'cosinnus.backends.EmailAuthBackend'
    user.save()
    
    return user


def get_newly_registered_user_email(user):
    """ Safely gets a user object's email address, even if they have yet to veryify their email address
        (in this case, the `user.email` field is scrambled.
        See `cosinnus.views.user.set_user_email_to_verify()` """
    from cosinnus.models.profile import PROFILE_SETTING_EMAIL_TO_VERIFY
    return user.cosinnus_profile.settings.get(PROFILE_SETTING_EMAIL_TO_VERIFY, user.email)


def get_user_select2_pills(users, text_only=False):
    from cosinnus.templatetags.cosinnus_tags import full_name
    return [(
         "user:" + six.text_type(user.id), 
         render_to_string('cosinnus/common/user_select2_pill.html', {'user': user}).replace('\n', '').replace('\r', '') if not text_only else escape(full_name(user)),
         ) for user in users]


def get_group_select2_pills(groups, text_only=False):
    return [(
         "group:" + six.text_type(group.id), 
         render_to_string('cosinnus/common/group_select2_pill.html', {'text':escape(group.name)}).replace('\n', '').replace('\r', '') if not text_only else escape(group.name),
         ) for group in groups]


def get_list_unsubscribe_url(email):
    """ Generates a URL to be used for a List-Unsubscribe header. Util function. """
    global _CosinnusPortal
    if _CosinnusPortal is None: 
        _CosinnusPortal = apps.get_model('cosinnus', 'CosinnusPortal')
    domain = get_domain_for_portal(_CosinnusPortal.get_current())
    return domain + reverse('cosinnus:user-add-email-blacklist', kwargs={'email': email, 'token': email_blacklist_token_generator.make_token(email)})


def accept_user_tos_for_portal(user, profile=None, portal=None, save=True):
    """ Saves that the user has accepted this portal's ToS.
        @param profile: if supplied, will use the given profile instance instead of querying it from the user. """
    if portal is None:
        from cosinnus.models.group import CosinnusPortal
        portal = CosinnusPortal.get_current()
    
    # set the user's tos_accepted flag to true and date for this portal to now
    if profile is None:
        profile = user.cosinnus_profile
    profile.settings['tos_accepted'] = True
    
    # save the accepted date for this portal in a new dict, or update the dict for this portal
    # (the old style setting for this only had a datetime saved, now we use a dict)
    portal_dict_or_date = user.cosinnus_profile.settings.get('tos_accepted_date', None)
    if portal_dict_or_date is None or type(portal_dict_or_date) is not dict:
        profile.settings['tos_accepted_date'] = {str(portal.id): now()}
    else:
        portal_dict_or_date[portal.id] = now()
        profile.settings['tos_accepted_date'] = portal_dict_or_date
    
    if save:
        profile.save()


def check_user_has_accepted_any_tos(user):
    """ Checks if the user has accepted any ToS ever, of any portal """
    return user.cosinnus_profile.settings.get('tos_accepted', False)


def check_user_has_accepted_portal_tos(user):
    """ Checks if the user has accepted the ToS of this portal before """
    return check_user_has_accepted_any_tos(user) and (get_user_tos_accepted_date(user) is not None)

    
def get_user_tos_accepted_date(user):
    """ Gets the datetime the user accepted this portals ToS, or None if they have not accepted it yet. 
        @return: a Datetime object or None
    """
    from cosinnus.models.group import CosinnusPortal
    portal = CosinnusPortal.get_current()
    portal_dict_or_date = user.cosinnus_profile.settings.get('tos_accepted_date', None)
    if portal_dict_or_date is None:
        if check_user_has_accepted_any_tos(user):
            # if user has accepted some ToS, but we don't know when, set it to in the past for this portal
            portal_dict_or_date = {str(portal.id): datetime.datetime(1999, 1, 1, 13, 37, 0, 0, pytz.utc)}
            user.cosinnus_profile.settings['tos_accepted_date'] = portal_dict_or_date
            user.cosinnus_profile.save(update_fields=['settings'])
            portal_dict_or_date = user.cosinnus_profile.settings.get('tos_accepted_date', None)
        else:
            return None
    if type(portal_dict_or_date) is not dict:
        # the old style setting for this only had a datetime saved, convert it to the modern
        # dict version of {<portal_id>: datetime, ...}
        portal_dict_or_date = {str(portal.id): portal_dict_or_date}
        user.cosinnus_profile.settings['tos_accepted_date'] = portal_dict_or_date
        user.cosinnus_profile.save(update_fields=['settings'])
    
    datetime_or_none = portal_dict_or_date.get(str(portal.id), None)
    if datetime_or_none is not None:
        if not type(datetime_or_none) is datetime.datetime:
            datetime_or_none = parser.parse(datetime_or_none)
        # we had a phase where we had unaware default datetimes saved, so backport-make them aware
        if is_naive(datetime_or_none):
            datetime_or_none = pytz.utc.localize(datetime_or_none)
    return datetime_or_none


def get_unread_message_count_for_user(user):
    """ Returns the unread message count for a user, independent of which internal
        messaging system is being used (Postman, Rocketchat, etc) """
    if not user.is_authenticated:
        return 0
    if getattr(settings, 'COSINNUS_ROCKET_ENABLED', False):
        from cosinnus_message.rocket_chat import RocketChatConnection # noqa
        unread_count = RocketChatConnection().unread_messages(user)
        
    else:
        from postman.models import Message
        unread_count = Message.objects.inbox_unread_count(user)
    return unread_count


def get_user_from_set_password_token(token):
    """ Checks if a token given as URL parameter for a user created without password is valid or not

    :param token: UUID4 send by mail as string
    :type token: str

    :rtype: user
    """
    from cosinnus.models.profile import PROFILE_SETTING_PASSWORD_NOT_SET

    USER_MODEL = get_user_model()

    # TODO this query could be simplified, if json field is imported by postgress library instead of django-jsonfield
    token_users = USER_MODEL.objects.filter(cosinnus_profile__settings__contains='password_not_set')

    for user in token_users:
        if user.cosinnus_profile.settings.get(PROFILE_SETTING_PASSWORD_NOT_SET, "") == token:
            return user

    return None
