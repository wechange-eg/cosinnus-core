"""
Custom fields.
"""

from __future__ import unicode_literals

from importlib import import_module

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES
from django.forms.fields import CharField
from django.utils.translation import gettext_lazy as _

from .models import get_user_name


class BasicCommaSeparatedUserField(CharField):
    """
    An internal base class for CommaSeparatedUserField.

    This class is not intended to be used directly in forms.
    Use CommaSeparatedUserField instead,
    to benefit from the auto-complete fonctionality if available.

    """

    default_error_messages = {
        'unknown': _('Some usernames are unknown or no longer active: {users}.'),
        'max': _('Ensure this value has at most {limit_value} distinct items (it has {show_value}).'),
        'min': _('Ensure this value has at least {limit_value} distinct items (it has {show_value}).'),
        'filtered': _('Some usernames are rejected: {users}.'),
        'filtered_user': _('{username}'),
        'filtered_user_with_reason': _('{username} ({reason})'),
    }

    def __init__(self, max=None, min=None, user_filter=None, *args, **kwargs):
        self.max, self.min, self.user_filter = max, min, user_filter
        label = kwargs.get('label')
        if isinstance(label, tuple):
            self.pluralized_labels = label
            kwargs.update(label=label[max == 1])
        super(BasicCommaSeparatedUserField, self).__init__(*args, **kwargs)

    def set_max(self, max):
        """Supersede the max value and ajust accordingly the label."""
        pluralized_labels = getattr(self, 'pluralized_labels', None)
        if pluralized_labels:
            self.label = pluralized_labels[max == 1]
        self.max = max

    def to_python(self, value):
        """Normalize data to an unordered list of distinct, non empty, whitespace-stripped strings."""
        value = super(BasicCommaSeparatedUserField, self).to_python(value)
        if value in EMPTY_VALUES:  # Return an empty list if no useful input was given.
            return []
        return list(set([name.strip() for name in value.split(',') if name and not name.isspace()]))

    def validate(self, value):
        """Check the limits."""
        super(BasicCommaSeparatedUserField, self).validate(value)
        if value in EMPTY_VALUES:
            return
        count = len(value)
        if self.max and count > self.max:
            raise ValidationError(self.error_messages['max'].format(limit_value=self.max, show_value=count))
        if self.min and count < self.min:
            raise ValidationError(self.error_messages['min'].format(limit_value=self.min, show_value=count))

    def clean(self, value):
        """Check names are valid and filter them."""
        names = super(BasicCommaSeparatedUserField, self).clean(value)
        if not names:
            return []
        user_model = get_user_model()
        name_user_as = getattr(settings, 'POSTMAN_NAME_USER_AS', user_model.USERNAME_FIELD)
        users = list(user_model.objects.filter(is_active=True, **{'{0}__in'.format(name_user_as): names}))
        unknown_names = set(names) ^ set([get_user_name(u) for u in users])
        errors = []
        if unknown_names:
            errors.append(self.error_messages['unknown'].format(users=', '.join(unknown_names)))
        if self.user_filter:
            filtered_names = []
            for u in users[:]:
                try:
                    reason = self.user_filter(u)
                    if reason is not None:
                        users.remove(u)
                        filtered_names.append(
                            self.error_messages['filtered_user_with_reason' if reason else 'filtered_user'].format(
                                username=get_user_name(u), reason=reason
                            )
                        )
                except ValidationError as e:
                    users.remove(u)
                    errors.extend(e.messages)
            if filtered_names:
                errors.append(self.error_messages['filtered'].format(users=', '.join(filtered_names)))
        if errors:
            raise ValidationError(errors)
        return users


d = getattr(settings, 'POSTMAN_AUTOCOMPLETER_APP', {})
app_name = d.get('name', 'ajax_select')
field_name = d.get('field', 'AutoCompleteField')
arg_name = d.get('arg_name', 'channel')
arg_default = d.get('arg_default')  # the minimum to declare to enable the feature

autocompleter_app = {}
if app_name in settings.INSTALLED_APPS and arg_default:
    autocompleter_app['is_active'] = True
    autocompleter_app['name'] = app_name
    autocompleter_app['version'] = getattr(import_module(app_name), '__version__', None)
    # does something like "from ajax_select.fields import AutoCompleteField"
    auto_complete_field = getattr(import_module(app_name + '.fields'), field_name)

    class CommaSeparatedUserField(BasicCommaSeparatedUserField, auto_complete_field):
        def __init__(self, *args, **kwargs):
            if not args and arg_name not in kwargs:
                kwargs.update([(arg_name, arg_default)])
            super(CommaSeparatedUserField, self).__init__(*args, **kwargs)

        def set_arg(self, value):
            """Same as it is done in ajax_select.fields.py for Fields and Widgets."""
            if hasattr(self, arg_name):
                setattr(self, arg_name, value)
            if hasattr(self.widget, arg_name):
                setattr(self.widget, arg_name, value)

else:
    autocompleter_app['is_active'] = False
    CommaSeparatedUserField = BasicCommaSeparatedUserField
