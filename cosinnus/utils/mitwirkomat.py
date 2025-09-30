# -*- coding: utf-8 -*-
import abc

from django.core.exceptions import ImproperlyConfigured

from cosinnus.dynamic_fields.dynamic_fields import CosinnusDynamicField


class AbstractMitwirkomatFilterExporter(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def export_mom_attribute(cls, value, field_class, mom):
        """
        Export the dynamic `CosinnusMitwirkomatDynamicField` as a filter for the Mitwirkomat, in the
        span-with-attributes format that is extended onto the description CSV field.
        This method should always return its full spectrum of attributes, even if the value in the mom settings are
        empty (in this case with empty attribute values).
        It is important to use single quotes for the attributes!

        @param value: the dynamic field value as saved in the model's `dynamic_fields`. This can be empty or None and
            must be handled accordingly!
        @param field_class: the `CosinnusMitwirkomatDynamicField` definition for the handled field
        @param mom: the `MitwirkomatSettings` instance which is being exported.
        @return: A string consisting of a string of one or more data-attributes in HTML style, or an empty string.
            These attributes MUST use single quotes!
            Example 1: "data-age='toddlers children'"
            Example 2: "data-parking='' data-tactile=''"
        """
        return NotImplemented


class MitwirkomatFilterExporterUnformatted(AbstractMitwirkomatFilterExporter):
    """Combines the dynamic field into a single data-attr that has as value the unformatted value of the dynamic field.
    Example:
    `<span class='filter-values' data-age='toddlers children'></span>`"""

    @classmethod
    def export_mom_attribute(cls, value, field_class, mom):
        return f"{field_class.mom_filter_attr_name}='{value or ''}'"


class MitwirkomatFilterExporterMultipleCombined(AbstractMitwirkomatFilterExporter):
    """Combines a multiple choice dynamic field into a single data-attr that has as value a space seperated list
    of all selected choices.
    It contains *only* the actually selected choices in that field.
    Example:
    `<span class='filter-values' data-age='toddlers children'></span>`"""

    @classmethod
    def export_mom_attribute(cls, value, field_class, mom):
        if value and isinstance(value, list):
            attribute_value = ' '.join(value)
        else:
            attribute_value = ''
        return f"{field_class.mom_filter_attr_name}='{attribute_value}'"


class MitwirkomatFilterExporterMultipleSeperate(AbstractMitwirkomatFilterExporter):
    """Combines a multiple choice dynamic field into a several data attributes where each is called "data-<CHOICEKEY>"
    and their value is `true` (without quotes) for selected choices, and empty for non-selected choices.
    It contains *all* possible choices as span.
    Example:
    `<span class='filter-values' data-parking='' data-tactile=''></span>`"""

    @classmethod
    def export_mom_attribute(cls, value, field_class, mom):
        if not field_class or not field_class.choices:
            raise ImproperlyConfigured(
                'MitwirkomatFilterExporterMultipleSeperate requires "choices" to be set in the dynamic field setting!'
            )
        attribute_strs = []
        # fill each attribute's value depending on if that choice key is saved in the dynamic field's multiple-list
        for choice_key, __ in field_class.choices:
            attribute_value = 'true' if isinstance(value, list) and choice_key in value else "''"
            attribute_strs.append(f'data-{choice_key}={attribute_value}')
        return ' '.join(attribute_strs)


class CosinnusMitwirkomatDynamicField(CosinnusDynamicField):
    """Definition for an extended dynamic extra field, e.g. for `settings.COSINNUS_MITWIRKOMAT_EXTRA_FIELDS`.
    Adds several properties to be able to configure Mitwirkomat filters with different export settings."""

    mom_filter_exporter = None  # a class ref to an implementing class of MitwirkomatFilterExporterBase
    mom_filter_attr_name = None  # for filter exporters that export a single tag: the complete name of that tag

    def __init__(self, **kwargs):
        # sanity check for required class attributes
        super().__init__(**kwargs)
        if not self.mom_filter_exporter:
            raise ImproperlyConfigured(
                f'CosinnusMitwirkomatDynamicField "{self.name}" requires kwarg "mom_filter_exporter" to be set!'
            )
