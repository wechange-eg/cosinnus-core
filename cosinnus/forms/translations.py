from django import forms


class TranslatedFieldsFormMixin(object):

    def get_field_type(self, field):
        return self.instance._meta.get_field(
            field).get_internal_type()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.languages and self.instance.get_translateable_fields():
            field_map = {}
            for field in self.instance.get_translateable_fields():
                for language in self.instance.languages:
                    field_name = '{}_translation_{}'.format(field, language[0])
                    field_type = self.get_field_type(field)
                    if field_type == 'CharField':
                        self.fields[field_name] = forms.CharField(
                            label=language[1],
                            required=False)
                    elif field_type == 'TextField':
                        self.fields[field_name] = forms.CharField(
                            widget=forms.Textarea,
                            label=language[1],
                            required=False)
                    field_map[field_name] = self.fields[field_name]
            setattr(self, 'translatable_field_list', field_map.keys())
            setattr(self, 'translatable_field_items', field_map.items())
            self.prepare_data_for_form()

    def prepare_data_for_form(self):
        for key in self.instance.translations.keys():
            translations = self.instance.translations.get(key)
            if translations:
                for lang in translations.keys():
                    self.initial['{}_translation_{}'.format(
                        key,
                        lang)] = translations.get(lang)

    def full_clean(self):
        super().full_clean()
        if hasattr(self, 'cleaned_data'):
            form_translations = self.cleaned_data
            object_translations = self.instance.translations
            for field in self.instance.get_translateable_fields():
                if not object_translations.get(field):
                    object_translations[field] = {}
                for lang in self.instance.languages:
                    form_field_name = '{}_translation_{}'.format(
                        field, lang[0])
                    if form_translations.get(form_field_name):
                        object_translations.get(
                            field)[lang[0]] = form_translations.get(
                            form_field_name)

            self.instance.translations = object_translations
