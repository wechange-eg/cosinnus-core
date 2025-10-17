import datetime
import logging
import pickle
import zlib
from abc import ABC, abstractmethod
from threading import Thread
from typing import Literal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import QuerySet
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.dynamic_fields import dynamic_fields
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.storage import TemporaryData
from cosinnus.utils.group import get_cosinnus_group_model


class ModelExportProcessor(ABC):
    """
    A threaded and extendable model export processor. Exports the data specified in CSV_EXPORT_COLUMNS_TO_FIELD_MAP as
    CSV. Keeping the export state in the cache. The exported CSV data is stored in a TemporaryData object.
    """

    # Export processor states
    STATE_EXPORT_READY = 'ready'
    STATE_EXPORT_RUNNING = 'running'
    STATE_EXPORT_FINISHED = 'finished'
    STATE_EXPORT_ERROR = 'error'

    # Main definition of exported data. Keys specify the columns and are used for the header line per default.
    # Values can contain a model field, a cosinnus_profile field, a dynamic_fields value or a custom processor function.
    # The respective case will be determined automatically using getattr.
    # Custom processor function should have a model-object as the argument. Example:
    # CSV_EXPORT_COLUMNS_TO_FIELD_MAP = {
    #   'column_name1': 'model_field1',      # model field value
    #   'column_name2': 'model_field2',      # model field value
    #   'column_name3': 'get_other_data',    # return value of the 'get_other_data(self, model)' function.
    # }

    CSV_EXPORT_COLUMNS_TO_FIELD_MAP = {}

    # Timeout for the export data
    EXPORT_CACHE_TIMEOUT = 60 * 60 * 24  # 1 day

    _EXPORT_CACHE_KEY_FORMAT = 'cosinnus/core/portal/%d/export/%s/%s'

    def _get_cache_key(self, cache_type: Literal['state', 'data_id', 'timestamp']) -> str:
        """
        :param cache_type: state: Current export state,
                           data_id: TemporaryData instance id containing the latest finished csv export data,
                           timestamp: Timestamp of the latest finished csv export
        :return: complete cache key for the current class
        """
        return self._EXPORT_CACHE_KEY_FORMAT % (CosinnusPortal.get_current().id, type(self).__name__, cache_type)

    def set_current_export_state(self, state):
        cache.set(self._get_cache_key('state'), state, self.EXPORT_CACHE_TIMEOUT)

    def get_current_export_state(self):
        return cache.get(self._get_cache_key('state'))

    def set_current_export_csv(self, csv):
        """
        Compress and store the export CSV data. The data is stored in a TemporaryData instance. The instnace id is
        stored in the cache.
        """
        picked_csv = pickle.dumps(csv)
        compressed_csv = zlib.compress(picked_csv)
        delete_csv_data_after = now() + datetime.timedelta(seconds=self.EXPORT_CACHE_TIMEOUT)
        temporary_data = TemporaryData.objects.create(
            deletion_after=delete_csv_data_after, description='Export Data', data=compressed_csv
        )
        cache.set(
            self._get_cache_key('data_id'),
            temporary_data.id,
            self.EXPORT_CACHE_TIMEOUT,
        )

    def get_current_export_csv(self):
        """Get and decompress the exported CSV data."""
        temporary_data_id = cache.get(self._get_cache_key('data_id'))
        if temporary_data_id and TemporaryData.objects.filter(id=temporary_data_id).exists():
            temporary_data = TemporaryData.objects.get(id=temporary_data_id)
            pickled_csv = zlib.decompress(temporary_data.data)
            csv = pickle.loads(pickled_csv)
            return csv

    def set_current_export_timestamp(self, timestamp):
        cache.set(self._get_cache_key('timestamp'), timestamp, self.EXPORT_CACHE_TIMEOUT)

    def get_current_export_timestamp(self):
        return cache.get(self._get_cache_key('timestamp'))

    def delete_export_cache(self):
        cache.delete(self._get_cache_key('state'))
        cache.delete(self._get_cache_key('data_id'))
        cache.delete(self._get_cache_key('timestamp'))

    def get_state(self):
        """Returns the current processor state."""
        export_state = self.get_current_export_state()
        state = export_state if export_state else self.STATE_EXPORT_READY
        return state

    @abstractmethod
    def get_model_queryset(self) -> QuerySet:
        """Model queryset used for the export."""

    def get_header(self):
        """Returns the export CSV header. Default: CSV_EXPORT_COLUMNS_TO_FIELD_MAP keys."""
        return self.CSV_EXPORT_COLUMNS_TO_FIELD_MAP.keys()

    @abstractmethod
    def export_single_model_row(self, obj):
        """
        Exports the data for a single model-object.
        """

    def _start_export(self, objects):
        """
        Main export function that can be called in a thread. Creates a CSV response file object and populates it with
        export data. Sets the state cache and csv file cache values according to the progress.
        """
        data = []
        timestamp = now()
        self.set_current_export_state(self.STATE_EXPORT_RUNNING)
        self.set_current_export_timestamp(timestamp)
        try:
            for obj in objects:
                obj_row = self.export_single_model_row(obj)
                data.append(obj_row)

            self.set_current_export_csv(data)
            self.set_current_export_state(self.STATE_EXPORT_FINISHED)

        except Exception as e:
            logging.exception(e)
            self.delete_export_cache()
            self.set_current_export_state(self.STATE_EXPORT_ERROR)

    def do_export(self, threaded=True):
        """Does a threaded data export. Threading can be disabled via the threaded parameter."""
        objects = list(self.get_model_queryset())
        if threaded:
            my_self = self

            class CosinnusExportProcessThread(Thread):
                def run(self):
                    my_self._start_export(objects)

            CosinnusExportProcessThread().start()
        else:
            self._start_export(objects)

    def delete_export(self):
        """Deletes all export data."""
        self.delete_export_cache()


class UserExportProcessorBase(ModelExportProcessor):
    """
    A threaded and extendable user export processor. Exports the data specified in CSV_EXPORT_COLUMNS_TO_FIELD_MAP as
    CSV. Keeping the export state in the cache. The exported CSV data is stored in a TemporaryData object.
    """

    CSV_EXPORT_COLUMNS_TO_FIELD_MAP = {
        'id': 'id',
        'first_name': 'first_name',
        'last_name': 'last_name',
        'email': 'email',
    }

    def get_model_queryset(self) -> QuerySet:
        """User queryset used for the user export."""
        qs = get_user_model().objects.all()
        qs = qs.select_related('cosinnus_profile').all()
        qs = qs.order_by('last_name', 'first_name')
        return qs

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
        if field_type in [
            dynamic_fields.DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT,
            dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        ]:
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

    def export_single_model_row(self, obj):
        """
        Exports the data for a single user. For each value of CSV_EXPORT_COLUMNS_TO_FIELD_MAP it determines if it is a
        user, cosinnus_profile, dynamic_fields value or processor function. Dynamic fields values are formatted using
        format_dynamic_field_value().
        """
        user = obj
        row = []
        for field in self.CSV_EXPORT_COLUMNS_TO_FIELD_MAP.values():
            value = ''
            if hasattr(self, field):
                value = getattr(self, field)(user)
            elif hasattr(user, field):
                value = getattr(user, field)
            elif hasattr(user, 'cosinnus_profile') and hasattr(user.cosinnus_profile, field):
                value = getattr(user.cosinnus_profile, field)
            elif hasattr(user, 'cosinnus_profile') and field in user.cosinnus_profile.dynamic_fields:
                field_value = user.cosinnus_profile.dynamic_fields[field]
                if field_value is not None:
                    value = self.format_dynamic_field_value(field, field_value)
            if value is None:
                value = ''
            row.append(value)
        return row


class GroupExportProcessorBase(ModelExportProcessor):
    """
    A threaded and extendable group export processor. Exports the data specified in CSV_EXPORT_COLUMNS_TO_FIELD_MAP as
    CSV. Keeping the export state in the cache. The exported CSV data is stored in a TemporaryData object.
    """

    # Main definition of exported data. Keys specify the columns and are used for the header line per default.
    # Values can contain a group field, a cosinnus_profile field, a dynamic_fields value or a custom processor function.
    # The respective case will be determined automatically using getattr. Custom processor function should have group as
    # the argument. Example:
    # CSV_EXPORT_COLUMNS_TO_FIELD_MAP = {
    #   'name': 'last_name',       # group field value
    #   'website': 'website',      # cosinnus_profile field value
    #   'pronoun': 'pronoun',      # dynamic_fields value
    #   'address': 'get_address',  # return value of the 'get_address(self, group)' function.
    # }
    CSV_EXPORT_COLUMNS_TO_FIELD_MAP = {
        'id': 'id',
        'name': 'name',
    }

    def get_model_queryset(self) -> QuerySet:
        """Group queryset used for the group export."""
        qs = get_cosinnus_group_model().objects.all()
        qs = qs.order_by('id')
        return qs

    def export_single_model_row(self, obj):
        """
        Exports the data for a single group. For each value of CSV_EXPORT_COLUMNS_TO_FIELD_MAP it determines if it is a
        group, cosinnus_profile, dynamic_fields value or processor function. Dynamic fields values are formatted using
        format_dynamic_field_value().
        """
        group = obj
        row = []
        for field in self.CSV_EXPORT_COLUMNS_TO_FIELD_MAP.values():
            value = ''
            if hasattr(self, field):
                value = getattr(self, field)(group)
            elif hasattr(group, field):
                value = getattr(group, field)
            if value is None:
                value = ''
            row.append(value)
        return row
