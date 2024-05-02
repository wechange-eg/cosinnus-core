# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from concurrent.futures import ThreadPoolExecutor, Future
from contextlib import wraps
from cosinnus_cloud.utils.nextcloud import rename_group_and_group_folder
import logging
import re
from threading import Thread
from time import sleep

from django.db.models.signals import post_save, post_delete
from django.db.utils import DatabaseError
from django.dispatch.dispatcher import receiver

from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.models import UserProfile
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety, \
    CosinnusConference
from cosinnus.utils.functions import is_number
from cosinnus.utils.group import get_cosinnus_group_model
from django.db.models.signals import post_save
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from django.db.utils import DatabaseError
from cosinnus_cloud.utils.cosinnus import is_cloud_enabled_for_group
from cosinnus.utils.user import is_user_active
from threading import Thread

from .utils import nextcloud


logger = logging.getLogger("cosinnus")


executor = ThreadPoolExecutor(max_workers=64, thread_name_prefix="nextcloud-req-")


def get_user_display_name(user):
    return user and hasattr(user, 'cosinnus_profile') and user.cosinnus_profile.get_external_full_name() or '(UNK)'


def submit_with_retry(fn, *args, **kwargs):
    @wraps(fn)
    def exec_with_retry():
        # seconds to wait before retrying.
        retry_wait = [2, 5, 10, 30, 60, 300]
        while True:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                try:
                    delay = retry_wait.pop(0)
                    logger.warning(
                        "Nextcloud call %s(%s, %s) failed. Retrying in %ds (%d tries left)",
                        fn.__name__,
                        args,
                        kwargs,
                        delay,
                        len(retry_wait),
                        exc_info=True,
                    )
                    sleep(delay)
                    continue
                except IndexError:
                    logger.warning(
                        "Nextcloud call %s(%s, %s) failed. Giving up",
                        fn.__name__,
                        args,
                        kwargs,
                        exc_info=True,
                    )
                    raise e

    executor.submit(exec_with_retry).add_done_callback(nc_req_callback)


def get_nc_user_id(user):
    return f"wechange-{user.id}"


def nc_req_callback(future: Future):
    try:
        res = future.result()
    except Exception:
        logger.exception("Nextcloud remote call resulted in an exception")
    else:
        logger.debug("Nextcloud call finished with result %r", res)



        
def disable_group_folder_for_group(group):
    """ For lack of a better way through the API, this 
        'disables' a group folder for a CosinnusGroup by removing the nextcloud group's access
        to the group folder, when a CosinnusGroup is deactivated """
    if group.nextcloud_group_id and group.nextcloud_groupfolder_id:
        submit_with_retry(
            nextcloud.remove_group_access_for_folder, 
            group.nextcloud_group_id,
            group.nextcloud_groupfolder_id
        )

def enable_group_folder_for_group(group):
    """ For lack of a better way through the API, this 
        'enables' a group folder for a CosinnusGroup by removing the nextcloud group's access
        to the group folder, when a CosinnusGroup is deactivated """
    if group.nextcloud_group_id and group.nextcloud_groupfolder_id:
        submit_with_retry(
            nextcloud.add_group_access_for_folder, 
            group.nextcloud_group_id,
            group.nextcloud_groupfolder_id
        )

    
def create_user_from_obj(user):
    """ Create a nextcloud user from a django auth User object """
    return nextcloud.create_user(
        get_nc_user_id(user),
        get_user_display_name(user),
        get_email_for_user(user),
    )

def update_user_from_obj(user):
    """ Called when a user updates their account. Updates NC account infos.
        Beware, this is a really slow endpoint! """
    nextcloud.update_user_name( 
        get_nc_user_id(user),
        get_user_display_name(user),
    )
    return nextcloud.update_user_email( 
        get_nc_user_id(user),
        get_email_for_user(user),
    )

def get_email_for_user(user):
    """ We currently set the user email to None, Nextcloud needs to send no emails anyways
        and this way it's more secure. """
    return ''

def generate_group_nextcloud_id(group, save=True, force_generate=False):
    """ See `generate_group_nextcloud_field` """
    return generate_group_nextcloud_field(group, 'nextcloud_group_id', save=save, force_generate=force_generate)


def generate_group_nextcloud_groupfolder_name(group, save=True, force_generate=False):
    """ See `generate_group_nextcloud_field` """
    return generate_group_nextcloud_field(group, 'nextcloud_groupfolder_name', save=save, force_generate=force_generate)


def generate_group_nextcloud_field(group, field, save=True, force_generate=False):
    """ If one doesn't yet exist, generates, saves and returns 
        a unique file-system-valid id that is used for both the 
        nextcloud group and group folder for this group. 
        Remove leading and trailing spaces; leave other spaces intact and remove 
        anything that is not an alphanumeric.
        @param field: The field for which a unique nextcloud name should be generated. Usually
            either `nextcloud_group_id` or `nextcloud_groupfolder_name`
        @param save: If True, the group will be saved to DB after generation
        @param force_generate: Generates a new id, even if one already exists
          """
    if hasattr(group, field) and getattr(group, field) and not force_generate:
        return getattr(group, field)

    filtered_name = str(group.name).strip().replace(" ", "-----")
    filtered_name = re.sub(r"(?u)[^\w-]", "", filtered_name)
    filtered_name = filtered_name.replace("-----", " ").strip()
    if getattr(settings, "COSINNUS_CLOUD_PREFIX_GROUP_FOLDERS", False):
        filtered_name = "%s %s" % (
            "G - "
            if group.type == get_cosinnus_group_model().TYPE_SOCIETY
            else "P - ",
            filtered_name,
        )
    elif not filtered_name or is_number(filtered_name):
        filtered_name = "Folder" + filtered_name
    # max length for nextcloud groups (group folders could be longer, but lets keep it like that)
    filtered_name = filtered_name[:64]  

    # uniquify the id-name in case it clashes
    all_names = list(set(
        get_cosinnus_group_model()
        .objects.filter(**{field + '__istartswith': filtered_name})
        .exclude(id=group.id)  # exclude self
        .values_list(field, flat=True)
    ))
    all_names = [name.lower() for name in all_names]
    all_names += [
        "admin"
    ]  # the admin group is a protected system group, so never assign it!

    counter = 2
    unique_name = filtered_name
    while unique_name.lower() in all_names:
        unique_name = "%s %d" % (filtered_name, counter)
        counter += 1
    
    setattr(group, field, unique_name)
    if save == True:
        group.save()
    return unique_name


def initialize_nextcloud_for_group(group):
    """ Initializes a nextcloud groupfolder for a group.
        Safe to call on already initialized folders. If called on a pre-existing folder that is 
        "disabled" (group has no more access to it), the group's access will be re-enabled for the folder. """
    if not is_cloud_enabled_for_group(group):
        return
    # generate group and groupfolder name if the group doesn't have one yet, or use the existing one
    generate_group_nextcloud_id(group, save=False)
    generate_group_nextcloud_groupfolder_name(group, save=False)
    try:
        # we need to only update these fields, as otherwise we could get save conflicts
        # if this method is called during group creation (m2m race conditions)
        group.save(update_fields=['nextcloud_group_id', 'nextcloud_groupfolder_name'])
    except DatabaseError as e:
        # we ignore save errors if the field values were unchanged
        if not 'did not affect any rows' in str(e):
            raise
    
    logger.debug(
        "Creating new group [%s] in Nextcloud (wechange group name [%s])",
        group.nextcloud_groupfolder_name,
        group.nextcloud_group_id,
    )
    
    # create nextcloud group
    nextcloud.create_group(group.nextcloud_group_id)
    # create nextcloud group folder
    nextcloud.create_group_folder(
        group.nextcloud_groupfolder_name,
        group.nextcloud_group_id,
        group,
        raise_on_existing_name=False,
    )
    # add admin user to group
    nextcloud.add_user_to_group(
        settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME,
        group.nextcloud_group_id
    )


# only activate these hooks when the cloud is enabled
if settings.COSINNUS_CLOUD_ENABLED:

    @receiver(signals.user_joined_group)
    def user_joined_group_receiver_sub(sender, user, group, **kwargs):
        """ Triggers when a user properly joined (not only requested to join) a group """
        # only initialize if the cosinnus-app is actually activated
        if user.is_guest:
            return
        if is_cloud_enabled_for_group(group):
            if group.nextcloud_group_id is not None:
                logger.debug(
                    "User [%s] joined group [%s], adding him/her to Nextcloud",
                    get_user_display_name(user),
                    group.name,
                )
                submit_with_retry(
                    nextcloud.add_user_to_group, get_nc_user_id(user), group.nextcloud_group_id
                )
    
    
    @receiver(signals.user_left_group)
    def user_left_group_receiver_sub(sender, user, group, **kwargs):
        """ Triggers when a user left a group.  
            Note: this can trigger on groups that do not have the cloud app activated, 
                  so that it removes users properly while the app is just disabled for 
                  a short period of time. """
        if user.is_guest:
            return
        if group.nextcloud_group_id is not None:
            logger.debug(
                "User [%s] left group [%s], removing him from Nextcloud",
                get_user_display_name(user),
                group.name,
            )
            submit_with_retry(
                nextcloud.remove_user_from_group,
                get_nc_user_id(user),
                group.nextcloud_group_id,
            )
    
    
    @receiver(signals.userprofile_created)
    def userprofile_created_sub(sender, profile, **kwargs):
        user = profile.user
        if user.is_guest:
            return
        logger.debug(
            "User profile created, adding user [%s] to nextcloud ", get_user_display_name(user)
        )
        submit_with_retry(create_user_from_obj, user)
    

    @receiver(post_save, sender=UserProfile)
    def handle_profile_updated(sender, instance, created, **kwargs):
        """
        # TODO: add a check which field should be updated (should only be the name, and only if it changed)
        
        # IMPORTANT: Needs to be threaded, because the endpoint is slooooow!
        """ 
        # only update active profiles 
        if created or not instance.id:
            return
        user = instance.user
        if user.is_guest:
            return
        if not is_user_active(user):
            return
        # run the update threaded because it is a very slow endpoint
        class UpdateNCUserThread(Thread):
            def run(self):
                try:
                    # we should actually use `update_user_from_obj`, but since
                    # the only field really updateable is the username (email is empty for now),
                    # we just use the direct method. and we don't submit_with_retry either,
                    # because if we fail this, we fail it
                    #submit_with_retry(update_user_from_obj, instance.user)
                    nextcloud.update_user_name( 
                        get_nc_user_id(user),
                        get_user_display_name(user),
                    )
                except Exception as e:
                    logger.warning('Could not update Nextcloud user on profile update.', extra={'exc': e})
        UpdateNCUserThread().start()
    
    
    @receiver(signals.group_object_created)
    def group_created_sub(sender, group, **kwargs):
        # only initialize if the cosinnus-app is actually activated
        if is_cloud_enabled_for_group(group):
            submit_with_retry(
                initialize_nextcloud_for_group,
                group
            )
        
        
    @receiver(signals.group_apps_activated)
    def group_cloud_app_activated_sub(sender, group, apps, **kwargs):
        """ Listen for the cloud app being activated """
        if 'cosinnus_cloud' in apps and is_cloud_enabled_for_group(group):
            def _conurrent_wrap():
                initialize_nextcloud_for_group(group)
                for user in group.actual_members:
                    submit_with_retry(
                        nextcloud.add_user_to_group, get_nc_user_id(user), group.nextcloud_group_id
                    )
                    # we don't need to remove users who have left the group while the app was deactivated here,
                    # because that listener is always active
            submit_with_retry(_conurrent_wrap)
    
    
    @receiver(signals.group_apps_deactivated)
    def group_cloud_app_deactivated_sub(sender, group, apps, **kwargs):
        # note: cannot use `is_cloud_enabled_for_group(group)` here, as it would fail since the app is already deactivated
        if 'cosinnus_cloud' in apps and settings.COSINNUS_CLOUD_ENABLED:
            disable_group_folder_for_group(group)
    
    
    def rename_nextcloud_groupfolder_on_group_rename(sender, created, **kwargs):
        """ Tries to rename the nextcloud group folder to reflect a Group's naming change """
        if not created:
            group = kwargs.get('instance')
            if is_cloud_enabled_for_group(group) and \
                    group.nextcloud_group_id and group.nextcloud_groupfolder_name and group.nextcloud_groupfolder_id:
                # just softly generate a new folder name first, and see if it has to be changed (because of a group rename)
                old_nextcloud_groupfolder_name = group.nextcloud_groupfolder_name
                generate_group_nextcloud_groupfolder_name(group, save=False, force_generate=True)
                new_nextcloud_groupfolder_name = group.nextcloud_groupfolder_name
                # rename the folder if the name would be a different one
                if new_nextcloud_groupfolder_name != old_nextcloud_groupfolder_name:
                    result = False
                    try:
                        result = rename_group_and_group_folder(group.nextcloud_groupfolder_id, new_nextcloud_groupfolder_name)
                    except Exception as e:
                        logger.warning('Could not rename Nextcloud group folder.', extra={'exc': e})
                    # if the rename was successful, save the new group folder name.
                    # otherwise, reload it to discard the newly generated folder name on the object
                    if result is True:
                        # Save the new group folder name. Not calling save() as it would re-trigger signals and also
                        # overwrite possible changes to group type during group type conversion.
                        get_cosinnus_group_model().objects.filter(pk=group.pk).update(nextcloud_groupfolder_name=new_nextcloud_groupfolder_name)
                        return
                group.refresh_from_db()
            
    post_save.connect(rename_nextcloud_groupfolder_on_group_rename, sender=get_cosinnus_group_model())
    post_save.connect(rename_nextcloud_groupfolder_on_group_rename, sender=CosinnusProject)
    post_save.connect(rename_nextcloud_groupfolder_on_group_rename, sender=CosinnusSociety)
    
    
    # maybe listen to user_logged_in and user_logged_out too?
    # https://docs.djangoproject.com/en/3.0/ref/contrib/auth/#django.contrib.auth.signals.user_logged_in
    
    
    @receiver(signals.user_deactivated)
    def user_deactivated(sender, user, **kwargs):
        if user.is_guest:
            return
        submit_with_retry(
            nextcloud.disable_user, 
            get_nc_user_id(user)
        )
    
    @receiver(signals.user_activated)
    def user_activated(sender, user, **kwargs):
        if user.is_guest:
            return
        submit_with_retry(
            nextcloud.enable_user, 
            get_nc_user_id(user)
        )
    
    @receiver(signals.pre_userprofile_delete)
    def user_deleted(sender, profile, **kwargs):
        """ Called when a user deletes their account. Completely deletes the user's nextcloud account """
        user = profile.user
        if user.is_guest:
            return
        submit_with_retry(
            nextcloud.delete_user, 
            get_nc_user_id(profile.user)
        )
        
    """
        TODO: we're missing an update-user hook to `nextcloud.update_user`!
    """
    
    
    @receiver(signals.group_deactivated)
    def group_deactivated(sender, group, **kwargs):
        if not is_cloud_enabled_for_group(group):
            return
        disable_group_folder_for_group(group)
    
    
    @receiver(signals.group_reactivated)
    def group_reactivated(sender, group, **kwargs):
        if not is_cloud_enabled_for_group(group):
            return
        enable_group_folder_for_group(group)
    
    
    @receiver(post_delete, sender=CosinnusProject)
    @receiver(post_delete, sender=CosinnusSociety)
    @receiver(post_delete, sender=CosinnusConference)
    def handle_group_deleted(sender, instance, **kwargs):
        """ Trigger to completely delete a group folder when a group is deleted.
            We have CosinnusConference in here as backwards compatibility, because for some conferences, 
            folders might have been created. """
        # note: cannot use `is_cloud_enabled_for_group(group)` here, as it would fail since the app is already deactivated
        group = instance
        if group.nextcloud_group_id and group.nextcloud_groupfolder_id and group.nextcloud_groupfolder_name:
            extra = {
                'group_id': group.id, 
                'group_slug': group.slug, 
                'nc_groupfolder_id': group.nextcloud_groupfolder_id, 
                'nc_group_id': group.nextcloud_group_id, 
                'nc_groupfolder_name': group.nextcloud_groupfolder_name,
            }
            logger.info('Nextcloud: Log: Deleting a groupfolder on group deletion.', extra=extra)
            submit_with_retry(
                nextcloud.delete_groupfolder, 
                group.nextcloud_groupfolder_id
            )
            submit_with_retry(
                nextcloud.delete_group, 
                group.nextcloud_group_id
            )
            logger.info('Nextcloud: Log: Deleted a groupfolder on group deletion.', extra=extra)
