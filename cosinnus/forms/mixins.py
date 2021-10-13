from django.conf import settings
from django.forms import all_valid

from cosinnus.utils.functions import resolve_class


class AdditionalFormsMixin(object):
    """Check additional forms and save them into JSON field"""
    dynamic_forms_setting = 'COSINNUS_PROJECT_ADDITIONAL_FORMS'
    dynamic_forms_field = 'dynamic_fields'

    @property
    def extra_forms(self):
        if not hasattr(self, '_dynamic_forms'):
            self._extra_forms = []
            initial = hasattr(self, 'instance') and getattr(self.instance, self.dynamic_forms_field) or None
            for form in getattr(settings, self.dynamic_forms_setting, []):
                form_class = resolve_class(form)
                if self.request.POST:
                    self._extra_forms.append(form_class(data=self.request.POST))
                else:
                    self._extra_forms.append(form_class(initial=initial))
        return self._extra_forms

    def is_valid(self):
        is_valid = super(AdditionalFormsMixin, self).is_valid()
        if len(self.extra_forms) > 0:
            return is_valid and all_valid(self.extra_forms)
        else:
            return is_valid

    def save(self, commit=True):
        self.instance = super(AdditionalFormsMixin, self).save(commit=False)
        dynamic_forms_field = getattr(self.instance, self.dynamic_forms_field)
        for extra_form in self.extra_forms:
            for field in extra_form:
                dynamic_forms_field[field.name] = field.data
        if commit:
            self.instance.save()
            self.save_m2m()
        return self.instance
