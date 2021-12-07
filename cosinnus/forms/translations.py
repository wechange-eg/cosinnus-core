from collections import defaultdict

from django import forms

from cosinnus.dynamic_fields.dynamic_formfields import EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS


class TranslatedFieldsFormMixin(object):

    def get_field_type(self, field):
        return self.instance._meta.get_field(
            field).get_internal_type()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        translatable_base_fields = self.instance.get_translateable_fields()
        if self.instance.languages and translatable_base_fields:
            field_map = {}
            for field in translatable_base_fields:
                for language in self.instance.languages:
                    field_name = '{}_translation_{}'.format(field, language[0])
                    field_type = self.get_field_type(field)
                    if field_type in ['CharField', 'TextField']:
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

            if self.instance.translatable_dynamic_fields and self.instance.dynamic_fields_settings:
                translatable_dynamic_fields = self.instance.translatable_dynamic_fields
                extra_fields = self.instance.dynamic_fields_settings

                for field in translatable_dynamic_fields:
                    dynamic_field = extra_fields.get(field)
                    for language in self.instance.languages:
                        field_name = '{}_translation_{}'.format(field, language[0])
                        dynamic_field_generator = EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS[dynamic_field.type]()
                        formfield = dynamic_field_generator.get_formfield(
                            field_name,
                            dynamic_field,
                            form=self
                        )
                        formfield.label = language[1]
                        self.fields[field_name] = formfield
                        field_map[field_name] = self.fields[field_name]
                translatable_base_fields = translatable_base_fields + translatable_dynamic_fields

            setattr(self, 'translatable_base_fields', translatable_base_fields)
            setattr(self, 'translatable_field_list', field_map.keys())
            setattr(self, 'translatable_field_items', field_map.items())
            setattr(self, 'translatable_fields_languages',
                    [language[0] for language in self.instance.languages])
            self.prepare_data_for_form()

    def prepare_data_for_form(self):
        for key in self.instance.translations.keys():
            if not key == 'dynamic_fields':
                translations = self.instance.translations.get(key)
                if translations:
                    for lang in translations.keys():
                        self.initial['{}_translation_{}'.format(
                            key,
                            lang)] = translations.get(lang)
            else:
                if self.instance.dynamic_fields and self.instance.translations.get('dynamic_fields'):
                    translations = self.instance.translations.get('dynamic_fields')
                    languages = translations.keys()
                    for lang in languages:
                        translation_fields = translations.get(lang).keys()
                        for field in translation_fields:
                            self.initial['{}_translation_{}'.format(field, lang)] = translations.get(lang).get(field)

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

                if self.instance.translatable_dynamic_fields:
                    if not object_translations.get('dynamic_fields'):
                        object_translations['dynamic_fields'] = {}

                    for lang in self.instance.languages:
                        for field in self.instance.translatable_dynamic_fields:
                            for lang in self.instance.languages:
                                form_field_name = '{}_translation_{}'.format(
                                    field, lang[0])
                                if form_translations.get(form_field_name):
                                    if not lang[0] in object_translations['dynamic_fields']:
                                        object_translations['dynamic_fields'][lang[0]] = {}
                                    object_translations['dynamic_fields'][lang[0]][field] = form_translations.get(
                                        form_field_name)

            self.instance.translations = object_translations
