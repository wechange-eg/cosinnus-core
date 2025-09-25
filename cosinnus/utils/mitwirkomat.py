# -*- coding: utf-8 -*-
from django.core.exceptions import ImproperlyConfigured

from cosinnus.dynamic_fields.dynamic_fields import CosinnusDynamicField


class MitwirkomatFilterDirectGenerator:
    """Combines any dynamic field into a single data-attr that has as value the unformatted value of the dynamic field.
    Example:
    `<span class='filter-values' data-age='toddlers children'></span>`"""

    @classmethod
    def generate_attribute_str_from_value(cls, value, field_class, mom):
        return f"{field_class.mom_attr_name}='{value}'"


class MitwirkomatFilterGeneratorMultipleCombined(MitwirkomatFilterDirectGenerator):
    """Combines a multiple choice dynamic field into a single data-attr that has as value a space seperated list
    of all selected choices. Example:
    `<span class='filter-values' data-age='toddlers children'></span>`"""

    @classmethod
    def generate_attribute_str_from_value(cls, value, field_class, mom):
        return f"{field_class.mom_attr_name}='{' '.join(value)}'"


class CosinnusMitwirkomatDynamicField(CosinnusDynamicField):
    """Definition for an extended dynamic extra field, e.g. for `settings.COSINNUS_MITWIRKOMAT_EXTRA_FIELDS`"""

    mom_generator = None  # a class ref to an implementing class of MitwirkomatFilterGeneratorBase
    mom_attr_name = None  # for filter generators that generate a single tag, the complete name of that tag

    def __init__(self, **kwargs):
        # sanity check
        super().__init__(**kwargs)
        if not self.mom_generator:
            raise ImproperlyConfigured(
                f'CosinnusMitwirkomatDynamicField "{self.name}" requires kwarg "mom_generator" to be set!'
            )
