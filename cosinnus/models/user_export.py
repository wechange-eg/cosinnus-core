import logging

from threading import Thread

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.dynamic_fields import dynamic_fields
from cosinnus.models.group import CosinnusPortal
from cosinnus.utils.functions import resolve_class


class CosinnusUserExportProcessorBase(object):
    """
    A threaded and extendable user export processor. Exports the data specified in CSV_EXPORT_COLUMNS_TO_FIELD_MAP as
    CSV. Keeping the export state and data in the cache.
    """

    # Export processor states
    STATE_EXPORT_READY = 'ready'
    STATE_EXPORT_RUNNING = 'running'
    STATE_EXPORT_FINISHED = 'finished'
    STATE_EXPORT_ERROR = 'error'

    # Main definition of exported data. Keys specify the columns and are used for the header line per default.
    # Values can contain a user field, a cosinnus_profile field, a dynamic_fields value or a custom processor function.
    # The respective case will be determined automatically using getattr. Custom processor function should have user as
    # the argument. Example:
    # CSV_EXPORT_COLUMNS_TO_FIELD_MAP = {
    #   'name': 'last_name',       # user field value
    #   'website': 'website',      # cosinnus_profile field value
    #   'pronoun': 'pronoun',      # dynamic_fields value
    #   'address': 'get_address',  # return value of the 'get_address(self, user)' function.
    # }
    CSV_EXPORT_COLUMNS_TO_FIELD_MAP = {
        'name': 'last_name',
        'first_name': 'first_name',
        'email': 'email',
    }

    # Timeout for the export data
    EXPORT_CACHE_TIMEOUT = 60*60*24  # 1 day

    # Current export state
    EXPORT_STATE_CACHE_KEY = 'cosinnus/core/portal/%d/export/state'

    # Latest finished csv export data
    EXPORT_CSV_CACHE_KEY = 'cosinnus/core/portal/%d/export/csv'

    # Timestamp of the latest finished csv export
    EXPORT_TIMESTAMP_CACHE_KEY = 'cosinnus/core/portal/%d/export/timestamp'

    def set_current_export_state(self, state):
        cache.set(self.EXPORT_STATE_CACHE_KEY % CosinnusPortal.get_current().id, state, self.EXPORT_CACHE_TIMEOUT)

    def get_current_export_state(self):
        return cache.get(self.EXPORT_STATE_CACHE_KEY % CosinnusPortal.get_current().id)

    def set_current_export_csv(self, csv):
        cache.set(self.EXPORT_CSV_CACHE_KEY % CosinnusPortal.get_current().id, csv, self.EXPORT_CACHE_TIMEOUT)

    def get_current_export_csv(self):
        return cache.get(self.EXPORT_CSV_CACHE_KEY % CosinnusPortal.get_current().id)

    def set_current_export_timestamp(self, timestamp):
        cache.set(self.EXPORT_TIMESTAMP_CACHE_KEY % CosinnusPortal.get_current().id, timestamp, self.EXPORT_CACHE_TIMEOUT)

    def get_current_export_timestamp(self):
        return cache.get(self.EXPORT_TIMESTAMP_CACHE_KEY % CosinnusPortal.get_current().id)

    def delete_export_cache(self):
        portal = CosinnusPortal.get_current().id
        cache.delete(self.EXPORT_STATE_CACHE_KEY % portal)
        cache.delete(self.EXPORT_CSV_CACHE_KEY % portal)
        cache.delete(self.EXPORT_TIMESTAMP_CACHE_KEY % portal)

    def get_state(self):
        """ Returns the current processor state. """
        export_state = self.get_current_export_state()
        state = export_state if export_state else self.STATE_EXPORT_READY
        return state

    def get_user_queryset(self):
        """ User queryset used for the user export. """
        qs = get_user_model().objects.all()
        qs = qs.select_related('cosinnus_profile').all()
        qs = qs.order_by('last_name', 'first_name')
        return qs

    def get_header(self):
        """ Returns the export CSV header. Default: CSV_EXPORT_COLUMNS_TO_FIELD_MAP keys. """
        return self.CSV_EXPORT_COLUMNS_TO_FIELD_MAP.keys()

    def format_dynamic_field_value(self, field, value):
        """
        Function called to automatically format dynamic fields values depending on the field type.
        - DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT and DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT:
            - multiple values are comma-seperated each quoted with quotation marks
            - single values are used directly
        - DYNAMIC_FIELD_TYPE_TEXT_AREA: linebreaks are removed
        - DYNAMIC_FIELD_TYPE_BOOLEAN: converted to "Yes" or "No"
        - Other: all other types are used directly
        Note: Consider using processor attribute functions for values of more complex types.
        """
        formatted_value = ''
        field_type = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS[field].type
        if field_type in [dynamic_fields.DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT, dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT]:
            multiple = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS[field].multiple
            if multiple:
                if len(value) > 1:
                    value = [f'"{subvalue}"' for subvalue in value]
                formatted_value = ', '.join(value)
            else:
                formatted_value = value
        elif field_type == dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT_AREA:
            formatted_value = ' '.join(value.splitlines())
        elif field_type == dynamic_fields.DYNAMIC_FIELD_TYPE_BOOLEAN:
            formatted_value = _('Yes') if value else _('No')
        else:
            formatted_value = value
        return formatted_value

    def export_single_user_row(self, user):
        """
        Exports the data for a single user. For each value of CSV_EXPORT_COLUMNS_TO_FIELD_MAP it determines if it is a
        user, cosinnus_profile, dynamic_fields value or processor function. Dynamic fields values are formatted using
        format_dynamic_field_value().
        """
        row = []
        for field in self.CSV_EXPORT_COLUMNS_TO_FIELD_MAP.values():
            value = ''
            if hasattr(self, field):
                value = getattr(self, field)(user)
            elif hasattr(user, field):
                value = getattr(user, field)
            elif hasattr(user.cosinnus_profile, field):
                value = getattr(user.cosinnus_profile, field)
            elif field in user.cosinnus_profile.dynamic_fields:
                field_value = user.cosinnus_profile.dynamic_fields[field]
                if field_value is not None:
                    value = self.format_dynamic_field_value(field, field_value)
            if value is None:
                value = ''
            row.append(value)
        return row

    def get_filename(self):
        """ Returns the file name used in the cached CSV/XLSX response file. """
        return 'user export'

    def _start_export(self, users):
        """
        Main export function that can be called in a thread. Creates a CSV response file object and populates it with
        user data. Sets the state cache and csv file cache values according to the progress.
        """
        data = []
        timestamp = now()
        self.set_current_export_state(self.STATE_EXPORT_RUNNING)
        self.set_current_export_timestamp(timestamp)
        try:
            for user in users:
                user_row = self.export_single_user_row(user)
                data.append(user_row)

            self.set_current_export_csv(data)
            self.set_current_export_state(self.STATE_EXPORT_FINISHED)

        except Exception as e:
            logging.exception(e)
            self.delete_export_cache()
            self.set_current_export_state(self.STATE_EXPORT_ERROR)

    def do_export(self, threaded=True):
        """ Does a threaded user export. Threading can be disabled via the threaded parameter. """
        users = self.get_user_queryset()
        if threaded:
            my_self = self

            class CosinnusUserExportProcessThread(Thread):
                def run(self):
                    my_self._start_export(users)
            CosinnusUserExportProcessThread().start()
        else:
            self._start_export(users)

    def delete_export(self):
        """ Deletes all export data. """
        self.delete_export_cache()


# allow dropin of export processor
CosinnusUserExportProcessor = CosinnusUserExportProcessorBase
if getattr(settings, 'COSINNUS_USER_EXPORT_PROCESSOR_CLASS_DROPIN', None):
    CosinnusUserExportProcessor = resolve_class(settings.COSINNUS_USER_EXPORT_PROCESSOR_CLASS_DROPIN)
