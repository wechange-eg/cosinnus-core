class JsonFieldFormsetMixin:
    """
    View Mixin to provide formset handling for data that is stored in a JSON-field list.
    Usage:

    1. Define a form that represents the data you want to store in the JSON-field list.

            class ExampleForm(forms.Form):
                value1 = forms.CharField()
                value2 = forms.IntegerField()

    2. Define a formset for your form.

        Set "can_delete" if deletion should be allowed.
        Set "extra=0" if adding should be disabled or "extra=<maximum>" otherwise.

            ExampleFormSet = formset_factory(ExampleForm, extra=10, can_delete=True)

    3. Include the JsonFieldFormsetMixin in your view and provide the configuration.

            class ExampleView(..., JsonFieldFormsetMixin, FormView):
                ...
                json_field_formsets = {
                    'example_json_field': ExampleFormSet,
                    'example_json_field2': ExampleFormSet2,
                }

        For dynamic formsets get_get_json_field_formsets() can be used to return the definition.

    4. Implement interface functions.

        The interface function 'get_instance' is required and should return the form instance if exists.
        The interface function 'json_field_formset_initial' is optional and should return a dict with initial values
        for each json-field formset and is used for its initialization if no instance is available.


            class ExampleView(..., JsonFieldFormsetMixin, FormView):
                ...
                def get_instance(self):
                    return instance

                def json_field_formset_initial(self):
                    return {
                        'example_json_field': [{'value1': 'test', 'value2': 1}, ...],
                        'example_json_field2': [...],
                    }

    5. Include the mixin hooks in your view logic.

        Include the json_field_formset_form_valid_hook() and json_field_formset_pre_save_hook() in the form_valid
        function. Also make sure, if you overwrite the form_invalid function to call super().

            class ExampleView(..., JsonFieldFormsetMixin, FormView):
                ...
                def form_valid(self, form):
                    json_field_formsets_valid = self.json_field_formset_form_valid_hook()
                    if not json_field_formsets_valid:
                        return self.form_invalid(form)
                    ...
                    instance = form.save(commit=False)
                    ...
                    self.json_field_formset_pre_save_hook(instance)
                    instance.save()
                    ...

    6. Define an inline template for the json-field form.

        example_inline_form.html:

            {% load i18n %}
            {% include 'cosinnus/fields/default_field.html' with field=inlineform.<field1> ... %}
            {% include 'cosinnus/fields/default_field.html' with field=inlineform.<field2> ... %}
            {{ inlineform.hidden_field }}

    7. Include the formsets into the template.

        The inline_form is added automatically to the context and is named "<json_field_name>_formset".

            {% include 'cosinnus/fields/inlineform_field.html' with inline_form=example_field_formset label=<label> content_template=<inline_form_template> unique_id='<id>' %}
    """  # noqa

    json_field_formsets = None
    _json_field_formset_instances = None

    def get_json_field_formsets(self):
        """Returns the formsets dict. Can be overwritten for dynamic formsets."""
        return self.json_field_formsets

    def get_instance(self):
        """Returns the instance with the json fields if available. Used for initialization."""
        raise NotImplementedError

    def json_field_formset_initial(self):
        """
        Returns a dict with initial formset values for each json field.
        Used for initialization if no instance is available.
        """
        return None

    def json_field_formset_form_valid_hook(self):
        """
        Hook that should be included in form_valid.
        Initializes the formsets on POST and returns if the formsets are valid.
        """
        self._init_formsets_on_post()
        return self._validate_formsets()

    def get_context_data(self, *args, **kwargs):
        """Adds formsets to the view context. Initializes the formsets if not already initialized (on GET)."""
        context = super(JsonFieldFormsetMixin, self).get_context_data(*args, **kwargs)
        if not self._json_field_formset_instances:
            self._init_formsets_on_get()
        context.update(
            {
                json_field_name + '_formset': formset
                for json_field_name, formset in self._json_field_formset_instances.items()
            }
        )
        return context

    def json_field_formset_pre_save_hook(self, instance):
        """Stores the formset values in the json field. Should be called before saving the form instance."""
        for json_field_name, formset_instance in self._json_field_formset_instances.items():
            formset_as_json = self._formset_as_json(formset_instance)
            setattr(instance, json_field_name, formset_as_json)

    def form_invalid(self, form):
        """Overwrites form_invalid to re-initialize formsets with submitted data."""
        self._init_formsets_on_post()
        self._validate_formsets()
        return super(JsonFieldFormsetMixin, self).form_invalid(form)

    def _init_formsets_on_get(self):
        """Initialize the formsets on GET."""
        instance = self.get_instance()
        if instance:
            # Initialize from instance
            initial = {
                json_field_name: getattr(instance, json_field_name)
                for json_field_name in self.get_json_field_formsets()
            }
        else:
            # Initialize with values provided by interface function
            initial = self.json_field_formset_initial()
        self._json_field_formset_instances = {}
        for json_field_name, formset in self.get_json_field_formsets().items():
            formset_instance = formset(prefix=json_field_name)
            if initial and json_field_name in initial:
                formset_instance.initial = initial[json_field_name]
            if not formset_instance.extra:
                # Setting max_num disables the "add" button if extra is not set or equals 0.
                formset_instance.max_num = len(initial[json_field_name])
            self._json_field_formset_instances[json_field_name] = formset_instance

    def _init_formsets_on_post(self):
        """Initialize formsets on POST."""
        self._json_field_formset_instances = {}
        for json_field_name, formset in self.get_json_field_formsets().items():
            formset_instance = formset(self.request.POST, self.request.FILES, prefix=json_field_name)
            self._json_field_formset_instances[json_field_name] = formset_instance

    def _validate_formsets(self):
        """Validates all formsets."""
        valid = True
        for formset_instance in self._json_field_formset_instances.values():
            formset_valid = formset_instance.is_valid()
            if not formset_valid:
                valid = False
        return valid

    def _formset_as_json(self, valid_formset_instance):
        """
        Converts the formset data to a JSON list. Store all fields directly as they are defined in the form.
        The extra "DELETE" value is removed from the data.
        """
        data = []
        for form_data in valid_formset_instance.cleaned_data:
            if form_data:
                if 'DELETE' in form_data:
                    if not form_data['DELETE']:
                        del form_data['DELETE']
                        data.append(form_data)
                else:
                    data.append(form_data)
        return data
