# -*- coding: utf-8 -*-
from django.core.exceptions import ImproperlyConfigured

from cosinnus.dynamic_fields.dynamic_fields import CosinnusDynamicField


class MitwirkomatFilterExporterUnformatted:
    """Combines the dynamic field into a single data-attr that has as value the unformatted value of the dynamic field.
    Example:
    `<span class='filter-values' data-age='toddlers children'></span>`"""

    @classmethod
    def export_mom_attribute(cls, value, field_class, mom):
        return f"{field_class.mom_filter_attr_name}='{value}'"


class MitwirkomatFilterExporterMultipleCombined(MitwirkomatFilterExporterUnformatted):
    """Combines a multiple choice dynamic field into a single data-attr that has as value a space seperated list
    of all selected choices. Example:
    `<span class='filter-values' data-age='toddlers children'></span>`"""

    @classmethod
    def export_mom_attribute(cls, value, field_class, mom):
        return f"{field_class.mom_filter_attr_name}='{' '.join(value)}'"


class CosinnusMitwirkomatDynamicField(CosinnusDynamicField):
    """Definition for an extended dynamic extra field, e.g. for `settings.COSINNUS_MITWIRKOMAT_EXTRA_FIELDS`"""

    mom_filter_exporter = None  # a class ref to an implementing class of MitwirkomatFilterExporterBase
    mom_filter_attr_name = None  # for filter exporters that export a single tag: the complete name of that tag

    def __init__(self, **kwargs):
        # sanity check
        super().__init__(**kwargs)
        if not self.mom_filter_exporter:
            raise ImproperlyConfigured(
                f'CosinnusMitwirkomatDynamicField "{self.name}" requires kwarg "mom_filter_exporter" to be set!'
            )
