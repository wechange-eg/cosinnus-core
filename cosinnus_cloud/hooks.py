# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import re
from base64 import b64encode
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import wraps
from threading import Thread
from time import sleep

from django.db.models.signals import post_delete, post_save
from django.db.utils import DatabaseError
from django.dispatch.dispatcher import receiver

from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.models import UserProfile
from cosinnus.models.group_extra import CosinnusConference, CosinnusProject, CosinnusSociety
from cosinnus.utils.functions import is_number
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.user import is_user_active
from cosinnus_cloud.utils.cosinnus import is_cloud_enabled_for_group, is_cloud_group_required_for_group
from cosinnus_cloud.utils.nextcloud import rename_group_folder, set_group_display_name

from .utils import nextcloud

logger = logging.getLogger('cosinnus')


executor = ThreadPoolExecutor(max_workers=64, thread_name_prefix='nextcloud-req-')


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
                        'Nextcloud call %s(%s, %s) failed. Retrying in %ds (%d tries left)',
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
                        'Nextcloud call %s(%s, %s) failed. Giving up',
                        fn.__name__,
                        args,
                        kwargs,
                        exc_info=True,
                    )
                    raise e

    executor.submit(exec_with_retry).add_done_callback(nc_req_callback)


def get_nc_user_id(user):
    return f'wechange-{user.id}'


def nc_req_callback(future: Future):
    try:
        res = future.result()
    except Exception:
        logger.exception('Nextcloud remote call resulted in an exception')
    else:
        logger.debug('Nextcloud call finished with result %r', res)


def disable_group_folder_for_group(group):
    """For lack of a better way through the API, this
    'disables' a group folder for a CosinnusGroup by removing the nextcloud group's access
    to the group folder, when a CosinnusGroup is deactivated"""
    if group.nextcloud_group_id and group.nextcloud_groupfolder_id:
        submit_with_retry(
            nextcloud.remove_group_access_for_folder, group.nextcloud_group_id, group.nextcloud_groupfolder_id
        )


def enable_group_folder_for_group(group):
    """For lack of a better way through the API, this
    'enables' a group folder for a CosinnusGroup by removing the nextcloud group's access
    to the group folder, when a CosinnusGroup is deactivated"""
    if group.nextcloud_group_id and group.nextcloud_groupfolder_id:
        submit_with_retry(
            nextcloud.add_group_access_for_folder, group.nextcloud_group_id, group.nextcloud_groupfolder_id
        )


def create_user_from_obj(user):
    """Create a nextcloud user from a django auth User object"""
    return nextcloud.create_user(
        get_nc_user_id(user),
        get_user_display_name(user),
        get_email_for_user(user),
    )


def update_user_from_obj(user):
    """Called when a user updates their account. Updates NC account infos.
    Beware, this is a really slow endpoint!"""
    nextcloud.update_user_name(
        get_nc_user_id(user),
        get_user_display_name(user),
    )
    return nextcloud.update_user_email(
        get_nc_user_id(user),
        get_email_for_user(user),
    )


def update_user_profile_avatar(profile, retry=False):
    """Update user avatar"""
    avatar_encoded = None
    if profile.avatar:
        # avatar changed, using a thumbnail the same size as the avatar in NextCloud
        avatar_file = profile.get_avatar_thumbnail(size=(512, 512))
        try:
            with avatar_file.open() as file:
                avatar_content = file.read()
                avatar_encoded = b64encode(avatar_content)
        except Exception as e:
            logger.warning('Could not update Nextcloud user avatar.', extra={'exc': e})
    else:
        # avatar deleted, using jane-doe image base64 encoded as the nc plugin does not provide avatar deletion
        avatar_encoded = b'iVBORw0KGgoAAAANSUhEUgAAASwAAAEsCAMAAABOo35HAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAylpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNS1jMDIxIDc5LjE1NDkxMSwgMjAxMy8xMC8yOS0xMTo0NzoxNiAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6MjRGMDY2RDBFNjUzMTFFMzg4RTdERDE5MURGRDQ3RTgiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6MjRGMDY2Q0ZFNjUzMTFFMzg4RTdERDE5MURGRDQ3RTgiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIChXaW5kb3dzKSI+IDx4bXBNTTpEZXJpdmVkRnJvbSBzdFJlZjppbnN0YW5jZUlEPSJ4bXAuZGlkOmUzZGE5YjQ1LWMyZGMtNzc0Mi04OGY1LTM0NjU4ZTkwZjdhMSIgc3RSZWY6ZG9jdW1lbnRJRD0ieG1wLmRpZDplM2RhOWI0NS1jMmRjLTc3NDItODhmNS0zNDY1OGU5MGY3YTEiLz4gPC9yZGY6RGVzY3JpcHRpb24+IDwvcmRmOlJERj4gPC94OnhtcG1ldGE+IDw/eHBhY2tldCBlbmQ9InIiPz5KjURpAAAAIVBMVEXM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'  # noqa

    if avatar_encoded:
        nc_user_id = get_nc_user_id(profile.user)
        if retry:
            submit_with_retry(nextcloud.update_user_avatar, nc_user_id, avatar_encoded)
        else:
            nextcloud.update_user_avatar(nc_user_id, avatar_encoded)


def get_email_for_user(user):
    """Get the email that is set as email the nextcloud user profile.
    Default is to set the user email to None, Nextcloud needs to send no emails anyways
    and this way it's more secure."""
    email = ''
    email_func = settings.COSINNUS_CLOUD_USER_PROFILE_EMAIL_FUNC
    if email_func is not None and callable(email_func):
        email = email_func(user)
    return email


def generate_group_nextcloud_id(group, save=True, force_generate=False):
    """See `generate_group_nextcloud_field`"""
    return generate_group_nextcloud_field(group, 'nextcloud_group_id', save=save, force_generate=force_generate)


def generate_group_nextcloud_groupfolder_name(group, save=True, force_generate=False):
    """See `generate_group_nextcloud_field`"""
    return generate_group_nextcloud_field(group, 'nextcloud_groupfolder_name', save=save, force_generate=force_generate)


def generate_group_nextcloud_field(group, field, save=True, force_generate=False):
    """If one doesn't yet exist, generates, saves and returns
    a unique file-system-valid id that is used for both the
    nextcloud group and group folder for this group.
    Remove leading and trailing spaces; leave other spaces intact and remove
    anything that is not an alphanumeric.
    @param field: The field for which a unique nextcloud name should be generated. Usually
        either `nextcloud_group_id` or `nextcloud_groupfolder_name`
    @param save: If True, the group field will be saved to DB after generation
    @param force_generate: Generates a new id, even if one already exists
    """
    if hasattr(group, field) and getattr(group, field) and not force_generate:
        return getattr(group, field)

    filtered_name = str(group.name).strip().replace(' ', '-----')
    filtered_name = re.sub(r'(?u)[^\w-]', '', filtered_name)
    filtered_name = filtered_name.replace('-----', ' ').strip()
    if getattr(settings, 'COSINNUS_CLOUD_PREFIX_GROUP_FOLDERS', False):
        filtered_name = '%s %s' % (
            'G - ' if group.type == get_cosinnus_group_model().TYPE_SOCIETY else 'P - ',
            filtered_name,
        )
    elif not filtered_name or is_number(filtered_name):
        filtered_name = 'Folder' + filtered_name
    # max length for nextcloud groups (group folders could be longer, but lets keep it like that)
    filtered_name = filtered_name[:64].strip()

    # uniquify the id-name in case it clashes
    all_names = list(
        set(
            get_cosinnus_group_model()
            .objects.filter(**{field + '__istartswith': filtered_name})
            .exclude(id=group.id)  # exclude self
            .values_list(field, flat=True)
        )
    )
    all_names = [name.lower() for name in all_names]
    all_names += ['admin']  # the admin group is a protected system group, so never assign it!

    counter = 2
    unique_name = filtered_name
    while unique_name.lower() in all_names:
        unique_name = '%s %d' % (filtered_name, counter)
        counter += 1

    setattr(group, field, unique_name)
    if save is True:
        group.save(update_fields=[field])
    return unique_name


def initialize_nextcloud_for_group(group, send_initialized_signal=True):
    """Initializes a nextcloud groupfolder for a group.
    Safe to call on already initialized folders. If called on a pre-existing folder that is
    "disabled" (group has no more access to it), the group's access will be re-enabled for the folder.
    @param send_initialized_signal: Sending of initialized signal can be disabled to avoid concurrency issues.
    """
    if not is_cloud_group_required_for_group(group):
        # No app requires the nextcloud integration
        return

    # generate group if the group doesn't have one yet, or use the existing one
    generate_group_nextcloud_id(group, save=False)
    try:
        # we need to only update these fields, as otherwise we could get save conflicts
        # if this method is called during group creation (m2m race conditions)
        group.save(update_fields=['nextcloud_group_id'])
    except DatabaseError as e:
        # we ignore save errors if the field values were unchanged
        if 'did not affect any rows' not in str(e):
            raise

    logger.debug('Creating new group [%s] in Nextcloud.', group.nextcloud_group_id)

    # create nextcloud group
    nextcloud.create_group(group.nextcloud_group_id)

    # add admin user to group
    nextcloud.add_user_to_group(settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME, group.nextcloud_group_id)

    # send initialized signal
    if send_initialized_signal:
        signals.group_nextcloud_group_initialized.send(sender=group.__class__, group=group)

    logger.debug(
        'Creating new group folder [%s] in Nextcloud (wechange group name [%s])',
        group.nextcloud_groupfolder_name,
        group.nextcloud_group_id,
    )

    if is_cloud_enabled_for_group(group):
        # The cloud app is enabled for the group, create the group folder.

        # generate groupfolder name if the group doesn't have one yet, or use the existing one
        generate_group_nextcloud_groupfolder_name(group, save=False)
        try:
            # we need to only update these field, as otherwise we could get save conflicts
            # if this method is called during group creation (m2m race conditions)
            group.save(update_fields=['nextcloud_groupfolder_name'])
        except DatabaseError as e:
            # we ignore save errors if the field values were unchanged
            if 'did not affect any rows' not in str(e):
                raise

        # create nextcloud group folder
        nextcloud.create_group_folder(
            group.nextcloud_groupfolder_name,
            group.nextcloud_group_id,
            group,
            raise_on_existing_name=False,
        )


# only activate these hooks when the cloud is enabled
if settings.COSINNUS_CLOUD_ENABLED:

    @receiver(signals.user_joined_group)
    def user_joined_group_receiver_sub(sender, user, group, **kwargs):
        """Triggers when a user properly joined (not only requested to join) a group"""
        # only initialize if the cosinnus-app is actually activated
        if user.is_guest:
            return
        if is_cloud_group_required_for_group(group):
            if group.nextcloud_group_id is not None:
                logger.debug(
                    'User [%s] joined group [%s], adding him/her to Nextcloud',
                    get_user_display_name(user),
                    group.name,
                )
                submit_with_retry(nextcloud.add_user_to_group, get_nc_user_id(user), group.nextcloud_group_id)

    @receiver(signals.user_left_group)
    def user_left_group_receiver_sub(sender, user, group, **kwargs):
        """Triggers when a user left a group.
        Note: this can trigger on groups that do not have the cloud app activated,
              so that it removes users properly while the app is just disabled for
              a short period of time."""
        if user.is_guest:
            return
        if group.nextcloud_group_id is not None:
            logger.debug(
                'User [%s] left group [%s], removing him from Nextcloud',
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
        logger.debug('User profile created, adding user [%s] to nextcloud ', get_user_display_name(user))
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
                    # submit_with_retry(update_user_from_obj, instance.user)
                    nextcloud.update_user_name(
                        get_nc_user_id(user),
                        get_user_display_name(user),
                    )
                except Exception as e:
                    logger.warning('Could not update Nextcloud user on profile update.', extra={'exc': e})

        UpdateNCUserThread().start()

    @receiver(signals.userprofile_avatar_updated)
    def handle_profile_avatar_updated(sender, profile, **kwargs):
        """Update the user avatar."""
        update_user_profile_avatar(profile, retry=True)

    @receiver(signals.group_object_created)
    def group_created_sub(sender, group, **kwargs):
        # only initialize if the cosinnus-app is actually activated
        if is_cloud_group_required_for_group(group):
            submit_with_retry(initialize_nextcloud_for_group, group)

    @receiver(signals.group_apps_activated)
    def group_cloud_or_deck_app_activated_sub(sender, group, apps, **kwargs):
        """Listen for the cloud app or deck app being activated"""
        if 'cosinnus_cloud' in apps or 'cosinnus_deck' in apps:
            if is_cloud_group_required_for_group(group):

                def _conurrent_wrap():
                    initialize_nextcloud_for_group(group)
                    for user in group.actual_members:
                        submit_with_retry(nextcloud.add_user_to_group, get_nc_user_id(user), group.nextcloud_group_id)
                        # we don't need to remove users who have left the group while the app was deactivated here,
                        # because that listener is always active

                submit_with_retry(_conurrent_wrap)

    @receiver(signals.group_apps_deactivated)
    def group_cloud_app_deactivated_sub(sender, group, apps, **kwargs):
        # note: cannot use `is_cloud_enabled_for_group(group)` here, as it would fail since the app is already
        # deactivated
        if 'cosinnus_cloud' in apps and settings.COSINNUS_CLOUD_ENABLED:
            disable_group_folder_for_group(group)

    def rename_nextcloud_group_and_groupfolder_on_group_rename(sender, created, **kwargs):
        """
        Tries to rename the nextcloud group folder and change the group display name to reflect a Group's naming change.
        """
        if not created:
            group = kwargs.get('instance')
            if is_cloud_enabled_for_group(group):
                if group.nextcloud_group_id and group.nextcloud_groupfolder_name and group.nextcloud_groupfolder_id:
                    # just softly generate a new folder name first, and see if it has to be changed (because of a group
                    # rename)
                    old_nextcloud_groupfolder_name = group.nextcloud_groupfolder_name
                    generate_group_nextcloud_groupfolder_name(group, save=False, force_generate=True)
                    new_nextcloud_groupfolder_name = group.nextcloud_groupfolder_name
                    # rename the folder if the name would be a different one
                    if new_nextcloud_groupfolder_name != old_nextcloud_groupfolder_name:
                        result = False
                        try:
                            result = rename_group_folder(group.nextcloud_groupfolder_id, new_nextcloud_groupfolder_name)
                        except Exception as e:
                            logger.warning('Could not rename Nextcloud group folder.', extra={'exc': e})
                        # if the rename was successful, save the new group folder name.
                        # otherwise, reload it to discard the newly generated folder name on the object
                        if result is True:
                            # Save the new group folder name. Not calling save() as it would re-trigger signals and also
                            # overwrite possible changes to group type during group type conversion.
                            get_cosinnus_group_model().objects.filter(pk=group.pk).update(
                                nextcloud_groupfolder_name=new_nextcloud_groupfolder_name
                            )

                            # change the group display name
                            try:
                                set_group_display_name(group.nextcloud_group_id, new_nextcloud_groupfolder_name)
                            except Exception as e:
                                logger.warning('Could not change Nextcloud group display name.', extra={'exc': e})

                            return
                    group.refresh_from_db()

            elif is_cloud_group_required_for_group(group) and group.nextcloud_group_id:
                # Cloud is required but cloud app is not enabled, update the group display name.

                # Temporary generate a groupfolder name to use as display name
                generate_group_nextcloud_groupfolder_name(group, save=False, force_generate=True)
                new_nextcloud_groupfolder_name = group.nextcloud_groupfolder_name

                # Set the group display name.
                # Note: Did not find an API to get the current display name, so we just update it.
                try:
                    set_group_display_name(group.nextcloud_group_id, new_nextcloud_groupfolder_name)
                except Exception as e:
                    if '404' not in str(e):
                        # Ignore non-existing group in renaming hook.
                        logger.warning('Could not change Nextcloud group display name.', extra={'exc': e})

                # the folder name was used just to get the new display name, reset the group instance.
                group.refresh_from_db()

        return

    post_save.connect(rename_nextcloud_group_and_groupfolder_on_group_rename, sender=get_cosinnus_group_model())
    post_save.connect(rename_nextcloud_group_and_groupfolder_on_group_rename, sender=CosinnusProject)
    post_save.connect(rename_nextcloud_group_and_groupfolder_on_group_rename, sender=CosinnusSociety)

    # maybe listen to user_logged_in and user_logged_out too?
    # https://docs.djangoproject.com/en/3.0/ref/contrib/auth/#django.contrib.auth.signals.user_logged_in

    @receiver(signals.user_deactivated)
    def user_deactivated(sender, user, **kwargs):
        if user.is_guest:
            return
        submit_with_retry(nextcloud.disable_user, get_nc_user_id(user))

    @receiver(signals.user_activated)
    def user_activated(sender, user, **kwargs):
        if user.is_guest:
            return
        submit_with_retry(nextcloud.enable_user, get_nc_user_id(user))

    @receiver(signals.user_promoted_to_superuser)
    def user_promoted_to_superuser(sender, user, **kwargs):
        if user.is_guest:
            return
        submit_with_retry(nextcloud.add_user_to_admin_group, get_nc_user_id(user))

    @receiver(signals.user_demoted_from_superuser)
    def user_demoted_from_superuser(sender, user, **kwargs):
        if user.is_guest:
            return
        submit_with_retry(nextcloud.remove_user_from_admin_group, get_nc_user_id(user))

    @receiver(signals.pre_userprofile_delete)
    def user_deleted(sender, profile, **kwargs):
        """Called when a user deletes their account. Completely deletes the user's nextcloud account"""
        user = profile.user
        if user.is_guest:
            return
        submit_with_retry(nextcloud.delete_user, get_nc_user_id(profile.user))

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
        """Trigger to completely delete a group folder when a group is deleted.
        We have CosinnusConference in here as backwards compatibility, because for some conferences,
        folders might have been created."""
        # note: cannot use `is_cloud_enabled_for_group(group)` here, as it would fail since the app is already
        # deactivated
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
            submit_with_retry(nextcloud.delete_groupfolder, group.nextcloud_groupfolder_id)
            submit_with_retry(nextcloud.delete_group, group.nextcloud_group_id)
            logger.info('Nextcloud: Log: Deleted a groupfolder on group deletion.', extra=extra)
