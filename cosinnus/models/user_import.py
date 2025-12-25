# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import locale
import logging
import traceback
from builtins import object
from threading import Thread

import six
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import EmailValidator
from django.db import models, transaction
from django.template.loader import render_to_string
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.utils.functions import resolve_class

logger = logging.getLogger('cosinnus')


# this reads the environment and inits the right locale
try:
    locale.setlocale(locale.LC_ALL, ('de_DE', 'utf8'))
except Exception:
    locale.setlocale(locale.LC_ALL, '')


def validates(validator, value):
    """Turns the ValidationError into a boolean"""
    try:
        validator()(value)
        return True
    except ValidationError:
        return False


class CosinnusUserImportReportItems(object):
    text = None
    report_class = 'info'
    is_sub_report_item = False

    def __init__(self, text, report_class='info', is_sub_report_item=False):
        self.text = text
        self.report_class = report_class
        self.is_sub_report_item = is_sub_report_item

    def to_string(self):
        context = {
            'text': self.text,
            'report_class': self.report_class,
            'is_sub_report_item': self.is_sub_report_item,
        }
        return render_to_string('cosinnus/user_import/report_item.html', context=context)


@six.python_2_unicode_compatible
class CosinnusUserImport(models.Model):
    """Saves uploaded import data and report output so that a dry-run can be saved and the user can,
    after checking the report, finalize the import from the dry run.
    After importing, this saves as a log for the import.
    There should only ever be one CosinnusUserImport object with ANY state other than STATE_ARCHIVED!"""

    STATE_DRY_RUN_RUNNING = 0
    STATE_DRY_RUN_FINISHED_INVALID = 1
    STATE_DRY_RUN_FINISHED_VALID = 2
    STATE_IMPORT_RUNNING = 3
    STATE_IMPORT_FINISHED = 4
    STATE_IMPORT_FAILED = 5
    STATE_ARCHIVED = 6

    #: Choices for :attr:`state`: ``(int, str)``
    STATE_CHOICES = (
        (STATE_DRY_RUN_RUNNING, _('Dry run in progress')),
        (STATE_DRY_RUN_FINISHED_INVALID, _('Dry run finished, errors in CSV that prevent import')),
        (STATE_DRY_RUN_FINISHED_VALID, _('Dry run finished, waiting to start import')),
        (STATE_IMPORT_RUNNING, _('Import running')),
        (STATE_IMPORT_FINISHED, _('Import finished')),
        (STATE_IMPORT_FAILED, _('Import failed')),
        (STATE_ARCHIVED, _('Import archived')),
    )

    last_modified = models.DateTimeField(verbose_name=_('Last modified'), editable=False, auto_now=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Creator'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    state = models.PositiveSmallIntegerField(
        _('Import state'), blank=False, default=STATE_DRY_RUN_RUNNING, choices=STATE_CHOICES, editable=False
    )

    import_data = models.JSONField(
        default=dict,
        verbose_name=_('Import Data'),
        blank=True,
        help_text='Stores the uploaded CSV data',
        editable=False,
        encoder=DjangoJSONEncoder,
    )
    import_report_html = models.TextField(
        verbose_name=_('Import Report HTML'),
        help_text='Stores the generated report for what the import will do / has done.',
        blank=True,
    )

    user_report_items = None

    IMPORT_PROGRESS_CACHE_KEY = 'cosinnus/core/portal/%d/import/progress'

    class Meta(object):
        ordering = ('-last_modified',)
        verbose_name = _('Cosinnus User Import')
        verbose_name_plural = _('Cosinnus User Imports')

    def __init__(self, *args, **kwargs):
        self.user_report_items = []
        super(CosinnusUserImport, self).__init__(*args, **kwargs)

    def __str__(self):
        return f'<UserImport from {self.last_modified}>'

    def append_to_report(self, text, report_class='info'):
        """Adds a report text to the current report
        @param report_class: a str class. can be "error", "warning", "info" (default) or custom"""
        self.import_report_html += CosinnusUserImportReportItems(text, report_class).to_string()

    def generate_and_append_user_report(self, header_text, report_class='info'):
        """Makes a user report container item from all accrued `self.user_report_items`.
        Will add symbol markers of any of the contained items' error classes
        @param report_items: None or a list"""
        item_classes = list(set([item.report_class for item in self.user_report_items]))
        report_item_html = ''.join([item.to_string() for item in self.user_report_items])
        context = {
            'report_class': report_class,
            'header_text': header_text,
            'symbol_classes': item_classes,
            'report_item_html': report_item_html,
        }
        self.import_report_html += render_to_string('cosinnus/user_import/report_container_item.html', context=context)
        self.clear_user_report_items()

    def add_user_report_item(self, text, report_class='info'):
        """Makes a report item.
        @param report_class: a str class. can be "error", "warning", "info" (default) or custom"""
        self.user_report_items.append(CosinnusUserImportReportItems(text, report_class, is_sub_report_item=True))

    def clear_user_report_items(self):
        self.user_report_items = []

    def clear_report(self):
        self.import_report_html = ''

    def set_import_progress_cache(self, progress_string):
        """Sets the cache progress string"""
        cache.set(self.IMPORT_PROGRESS_CACHE_KEY % CosinnusPortal.get_current().id, progress_string, 60 * 60)

    def get_import_progress_cache(self):
        """Returns the cache progress string"""
        return cache.get(self.IMPORT_PROGRESS_CACHE_KEY % CosinnusPortal.get_current().id)

    def save(self, *args, **kwargs):
        # sanity check: if the to-be-saved state isn't STATE_ARCHIVED, make sure no other import exists that isn't
        # archived
        if self.state != CosinnusUserImport.STATE_ARCHIVED:
            created = bool(self.pk is None)
            existing_imports = CosinnusUserImport.objects.exclude(state=CosinnusUserImport.STATE_ARCHIVED)
            if not created:
                existing_imports = existing_imports.exclude(id=self.id)
            if existing_imports.count() > 0:
                raise Exception(
                    'CosinnusUserImport: Could not save import object because state check failed: there is another '
                    'import that is not archived.'
                )
        super(CosinnusUserImport, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('cosinnus:administration-archived-user-import-detail', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('cosinnus:administration-archived-user-import-delete', kwargs={'pk': self.id})


class CosinnusUserImportProcessorBase(object):
    # a mapping of column header names to user/userprofile/user-media-tag field names
    # important: the keys are *ALWAYS* lower-case as the CSV importer will lower().strip() them!
    CSV_HEADERS_TO_FIELD_MAP = {
        'email': 'email',
    }
    if settings.COSINNUS_USER_FORM_SHOW_SEPARATE_LAST_NAME:
        CSV_HEADERS_TO_FIELD_MAP.update(
            {
                'firstname': 'first_name',
                'lastname': 'last_name',
            }
        )
    else:
        CSV_HEADERS_TO_FIELD_MAP.update(
            {
                'displayname': 'first_name',
            }
        )

    # lower case list of all column names known and used for the import
    KNOWN_CSV_IMPORT_COLUMNS_HEADERS = CSV_HEADERS_TO_FIELD_MAP.keys()
    # required column headers to be present in the CSV data.
    # note: this does not mean the row data for this column is required, only the column should exist
    REQUIRED_CSV_IMPORT_COLUMN_HEADERS = KNOWN_CSV_IMPORT_COLUMNS_HEADERS
    # field names for csv entry row data that need to not be empty in order for the import of that row to be accepted
    # these are the *FIELD NAMES*, not the CSV column headers! so this is from `CSV_HEADERS_TO_FIELD_MAP.values()`!
    REQUIRED_FIELDS_FOR_IMPORT = [
        'email',
        'first_name',
    ]
    # reverse map of CSV_HEADERS_TO_FIELD_MAP, initialized on init
    field_name_map = None  # dict

    # a list of django.auth.Users created already during the run
    created_users = None  # dict

    # the user performing the import, or None
    import_creator = None

    def __init__(self):
        # init the reverse map here in case the header map gets changed in the cls
        self.field_name_map = dict([(val, key) for key, val in self.CSV_HEADERS_TO_FIELD_MAP.items()])
        self.created_users = []

    def do_import(self, user_import_item, dry_run=True, threaded=True, import_creator=None):
        """Does a threaded user import, either as a dry-run or real one.
        Will update the import object's state when done or failed.
        @property user_import_item: class `CosinnusUserImport` containing import_data
        @property import_creator: the user performing the import, or None.
            Needed for some import actions that require setting a creator
            (for example when creating groups)"""
        self.import_creator = import_creator
        if settings.DEBUG:
            threaded = True  # never thread in dev

        if dry_run:
            user_import_item.state = CosinnusUserImport.STATE_DRY_RUN_RUNNING
        else:
            user_import_item.state = CosinnusUserImport.STATE_IMPORT_RUNNING
        user_import_item.save()
        # start import
        my_self = self
        if threaded:

            class CosinnusUserImportProcessThread(Thread):
                def run(self):
                    my_self._start_import(user_import_item, dry_run=dry_run)

            CosinnusUserImportProcessThread().start()
        else:
            my_self._start_import(user_import_item, dry_run=dry_run)

    def _start_import(self, user_import_item, dry_run=True):
        """Baseline implementation for a very simple user import"""
        import_failed_overall = False

        total_items = len(user_import_item.import_data)
        imported_items = 0
        failed_items = 0

        try:
            # main atomic wrapper, a dry run will this to rollback at the very end
            with transaction.atomic():
                for item_data in user_import_item.import_data:
                    user_import_item.set_import_progress_cache(f'{imported_items + failed_items}/{total_items}')

                    # clear user item reports
                    user_import_item.clear_user_report_items()
                    # sanity check: all absolutely required fields must exist:
                    missing_fields = [
                        self.field_name_map[req_field]
                        for req_field in self.REQUIRED_FIELDS_FOR_IMPORT
                        if not item_data.get(self.field_name_map[req_field], None)
                    ]
                    if missing_fields:
                        import_successful = False
                        user_import_item.add_user_report_item(
                            _('CSV row did not contain data for required columns: "%(fields)s"')
                            % {'fields': '", "'.join(missing_fields), 'row_num': item_data['ROW_NUM'] + 1},
                            report_class='error',
                        )
                    else:
                        # NOTE: supplying dry_run=False here will still do an effective dry run because we
                        # rollback the transaction at the end!
                        # it will have some negative effects though, like rocketchat hooks triggering
                        import_successful = self._do_single_user_import(item_data, user_import_item, dry_run=dry_run)

                    report_class = 'info' if import_successful else 'error'
                    user_import_item.generate_and_append_user_report(
                        self.get_user_report_title(item_data), report_class
                    )
                    if import_successful:
                        imported_items += 1
                    else:
                        failed_items += 1

                    # instantly fail a real import when a single user could not be imported. this should have been
                    # caught by the dry-run validation (which wouldve disabled the real import), or hints at a serious
                    # relational problem that should be looked into
                    if not import_successful:
                        import_failed_overall = True
                        if not dry_run:
                            # prepend the error message
                            user_import_item.import_report_html = (
                                CosinnusUserImportReportItems(
                                    _(
                                        'Import for a user item has failed, cancelling the import process! '
                                        'TODO: has data been written?'
                                    ),
                                    'error',
                                ).to_string()
                                + user_import_item.import_report_html
                            )
                            break

                if dry_run or not import_failed_overall:
                    # add additional relational import logic which could not be assigned without the main
                    # import items existing
                    self._import_second_round_relations(user_import_item.import_data, user_import_item, dry_run=dry_run)

                # after loop: prepend summary message
                summary_message = (
                    str(_('Total Items'))
                    + f': {total_items}, '
                    + str(_('Items for Import'))
                    + f': {imported_items}, '
                    + str(_('Ignored/Failed Items'))
                    + f': {failed_items}, '
                )
                user_import_item.import_report_html = (
                    CosinnusUserImportReportItems(summary_message, 'info').to_string()
                    + user_import_item.import_report_html
                )

                # trigger a rollback for finished dry-runs
                if dry_run:
                    raise DryRunFinishedException()

                user_import_item.set_import_progress_cache(None)

        except Exception as e:
            if type(e) is DryRunFinishedException:
                # this means the dry-run finished properly and DB transactions have been rolled back
                pass
            else:
                # if this outside exception happens, the import will be declared as "no data has been imported" and the
                # errors will be shown
                stack_trace = traceback.format_exc()
                stack_trace = '\n'.join([line for line in reversed(stack_trace.split('\n'))])
                logger.error(
                    f'User Import: Critical failure during import (dry-run: {dry_run})',
                    extra={'exception': e, 'stack_trace': stack_trace},
                )
                import_failed_overall = True
                # prepend the error message
                user_import_item.import_report_html = (
                    CosinnusUserImportReportItems(str(e), 'error').to_string() + user_import_item.import_report_html
                )
                user_import_item.import_report_html = (
                    CosinnusUserImportReportItems(
                        _(
                            'An unexpected system error has occured while processing the data. This should not have '
                            'happened. Please contact the support! Technical Details follow:'
                        ),
                        'error',
                    ).to_string()
                    + user_import_item.import_report_html
                )

                if settings.DEBUG:
                    if dry_run:
                        user_import_item.state = CosinnusUserImport.STATE_DRY_RUN_FINISHED_INVALID
                    else:
                        user_import_item.state = CosinnusUserImport.STATE_IMPORT_FAILED
                    user_import_item.save()
                    raise e

        if import_failed_overall:
            if dry_run:
                user_import_item.state = CosinnusUserImport.STATE_DRY_RUN_FINISHED_INVALID
            else:
                user_import_item.state = CosinnusUserImport.STATE_IMPORT_FAILED
        else:
            if dry_run:
                user_import_item.state = CosinnusUserImport.STATE_DRY_RUN_FINISHED_VALID
            else:
                user_import_item.state = CosinnusUserImport.STATE_IMPORT_FINISHED
        user_import_item.save()

    def _do_single_user_import(self, item_data, user_import_item, dry_run=True):
        """Main import function for a single user data object.
        During this, user_item_reports should be accrued for the item
        @param item_data: A dict object containing keys corresponding to `KNOWN_CSV_IMPORT_COLUMNS_HEADERS` and the row
            data for one user
        @return: A django.auth.User object if successful, None if not"""
        check_valid = self._import_check_user_contraints_valid(item_data, user_import_item, dry_run=dry_run)
        if not check_valid:
            return False
        user = self._import_create_auth_user(item_data, user_import_item, dry_run=dry_run)
        if not user:
            return False
        self.created_users.append(user)
        return True

    def _import_check_user_contraints_valid(self, item_data, user_import_item, dry_run=True):
        """Checks constraints whether a valid user could be created from the import data (unique email).
        Will also check against any already created users!"""
        email = item_data.get(self.field_name_map['email']).lower()
        email_exists_db = get_user_model().objects.filter(email__iexact=email).exists()
        email_exists_import = any([bool(email == new_user.email) for new_user in self.created_users])
        if email_exists_db:
            user_import_item.add_user_report_item(
                _('The email-address already has an existing user account in the system!'), report_class='error'
            )
        if email_exists_import:
            user_import_item.add_user_report_item(
                _('The email-address is duplicated and already contained in the CSV!'), report_class='error'
            )
        if email_exists_db or email_exists_import:
            return False
        return True

    def _import_create_auth_user(self, item_data, user_import_item, dry_run=True):
        """Create a user object from import.
        @return: None if not successful, else a auth user object"""
        # fields are in REQUIRED_FIELDS_FOR_IMPORT so we can assume they exist
        email = item_data.get(self.field_name_map['email']).lower()
        first_name = item_data.get(self.field_name_map['first_name'], '')[:30]
        if settings.COSINNUS_USER_FORM_SHOW_SEPARATE_LAST_NAME:
            last_name = item_data.get(self.field_name_map['last_name'], '')[:30]
        else:
            last_name = None

        if not validates(EmailValidator, email):
            user_import_item.add_user_report_item(
                _('The email address was not a valid email address!'), report_class='error'
            )
            return None

        user_kwargs = {
            'username': email,
            'email': email,
            'first_name': first_name,
        }
        if last_name:
            user_kwargs['last_name'] = last_name
        user = get_user_model()(**user_kwargs)
        #
        if not dry_run:
            user.save()
            user.username = str(user.id)
            user.save()
            # CosinnusPortalMembership.objects.get_or_create(group=CosinnusPortal.get_current(), user=user,
            #                                                status=MEMBERSHIP_MEMBER)

        del user_kwargs['username']
        if not settings.COSINNUS_USER_FORM_SHOW_SEPARATE_LAST_NAME:
            user_kwargs['displayname'] = user_kwargs['first_name']
            del user_kwargs['first_name']
        user_import_item.add_user_report_item(str(_('New user account: ') + str(user_kwargs)), report_class='info')
        return user

    def _import_second_round_relations(self, item_data_list, user_import_item, dry_run=True):
        """Stub to support an additional, second import round for CSV items,
        run after the main import has been processed and all items have been created.
        Mainly enables things like group membership or tag assignments, which
        wouldn't work on a single pass of the imported data because they may
        reference data that follows further on in the CSV."""
        pass

    def get_user_report_title(self, item_data):
        return (
            'Row: #'
            + str(item_data['ROW_NUM'] + 1)
            + ' <b>'
            + item_data.get(self.field_name_map['first_name'], '(no name)')
            + '</b> <i>'
            + item_data.get(self.field_name_map['email'], '(no email)')
            + '</i>'
        )


class DryRunFinishedException(Exception):
    """An exception that rolls back an atomic block for a dry run when it has finished successfully."""

    pass


# allow dropin of labels class
CosinnusUserImportProcessor = CosinnusUserImportProcessorBase
if getattr(settings, 'COSINNUS_USER_IMPORT_PROCESSOR_CLASS_DROPIN', None):
    CosinnusUserImportProcessor = resolve_class(settings.COSINNUS_USER_IMPORT_PROCESSOR_CLASS_DROPIN)
