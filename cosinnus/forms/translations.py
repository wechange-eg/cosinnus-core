from django import forms

from cosinnus.dynamic_fields.dynamic_formfields import (
    EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS as field_generators)


class TranslatedFieldsFormMixin(object):
    """
    Adds extra fields (one for each language) to form.
    Fields that can be translated are defined in Model,
    they can either be model fields or fields from dynamic_fields.
    Translated field names have the structure
    <fieldname>_translation_<language_code>

    translations are saved liked that in model translations json field:
    {"<fieldname>":
        {"<language_code": "foo"},
        {"<another language_code": "bar"}
    }

    Special case - dynamic_fields:
    {"dynamic_fields":
        {"<language_code>":
            {"<fieldname": "foo"},
            {"<another fieldname": "bar"}
        }
    }
    Be aware: only fields with translations of dynamic_fields
    are added to the translations json.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model_fields = self.instance.get_translateable_fields()
        dynamic_fields = self.instance.translatable_dynamic_fields
        translatable_base_fields = model_fields + dynamic_fields
        if self.instance.languages and (model_fields or dynamic_fields):
            field_map = {}
            self.add_model_field_translation_fields(
                model_fields, field_map)
            self.add_dynamic_fields_translation_fields(
                dynamic_fields, field_map)

            setattr(self, 'translatable_base_fields', translatable_base_fields)
            setattr(self, 'translatable_field_items', field_map.items())
            setattr(self, 'translatable_fields_languages',
                    [language[0] for language in self.instance.languages])

            self.add_initial_data_for_model_fields()
            self.add_initial_data_for_dynamic_fields()

    def full_clean(self):
        super().full_clean()

        if hasattr(self, 'cleaned_data'):
            form_translations = self.cleaned_data
            object_translations = self.instance.translations
            self.add_model_translations_to_object(
                object_translations, form_translations)
            self.add_dynamic_fields_translations_to_object(
                object_translations, form_translations)
            self.instance.translations = object_translations

    def add_model_field_translation_fields(self, model_fields, field_map):
        """
        Create translation fields for fields from model based
        on fieldtype of model field, only Charfield and Textfield possible.
        """
        for field in model_fields:
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

    def get_field_type(self, field):
        return self.instance._meta.get_field(
            field).get_internal_type()

    def add_dynamic_fields_translation_fields(self, dynamic_fields, field_map):
        """
        Create translation fields for fields from dynamic_fields.
        The Fieldtype of fields in dynmaic_fields is defined in the
        settings, so a lookup there is needed in order to create the
        field with the formfield generator.
        """
        extra_fields = self.instance.dynamic_fields_settings
        if dynamic_fields and extra_fields:
            for field in dynamic_fields:
                dynamic_field = extra_fields.get(field)
                for language in self.instance.languages:
                    field_name = '{}_translation_{}'.format(field, language[0])
                    field_generator = field_generators[dynamic_field.type]()
                    formfield = field_generator.get_formfield(
                        field_name,
                        dynamic_field,
                        form=self
                    )
                    formfield.label = language[1]
                    self.fields[field_name] = formfield
                    field_map[field_name] = self.fields[field_name]

    def add_initial_data_for_model_fields(self):
        for key in self.instance.get_translateable_fields():
            if not key == 'dynamic_fields':
                translations = self.instance.translations.get(key)
                if translations:
                    for lang in translations.keys():
                        self.initial['{}_translation_{}'.format(
                            key,
                            lang)] = translations.get(lang)

    def add_initial_data_for_dynamic_fields(self):
        if 'dynamic_fields' in self.instance.translateable_fields:
            df = self.instance.dynamic_fields
            translations = self.instance.translations.get('dynamic_fields')
            if translations:
                if df and translations:
                    languages = translations.keys()
                    for lang in languages:
                        translation_fields = translations.get(lang).keys()
                        for field in translation_fields:
                            field_name = '{}_translation_{}'.format(
                                field, lang)
                            initial_value = translations.get(lang).get(field)
                            self.initial[field_name] = initial_value

    def add_model_translations_to_object(self, object_translations, form_data):
        for field in self.instance.get_translateable_fields():
            if not object_translations.get(field):
                object_translations[field] = {}
            for lang in self.instance.languages:
                form_field_name = '{}_translation_{}'.format(
                    field, lang[0])
                if form_data.get(form_field_name):
                    object_translations.get(
                        field)[lang[0]] = form_data.get(
                        form_field_name)

    def add_dynamic_fields_translations_to_object(self, object_translations, form_data):
        if self.instance.translatable_dynamic_fields:
            df_translations = object_translations.get('dynamic_fields', {})
            for lang in self.instance.languages:
                for field in self.instance.translatable_dynamic_fields:
                    for lang in self.instance.languages:
                        form_field_name = '{}_translation_{}'.format(
                            field, lang[0])
                        if form_data.get(form_field_name):
                            if not lang[0] in df_translations:
                                df_translations[lang[0]] = {}
                            df_translations[lang[0]][field] = form_data.get(
                                form_field_name)
            object_translations['dynamic_fields'] = df_translations
