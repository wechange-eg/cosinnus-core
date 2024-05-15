from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView

from cosinnus.forms.dynamic_fields import DynamicFieldAdminChoicesFormGenerator
from cosinnus.models import CosinnusPortal
from cosinnus.views.mixins.group import RequireSuperuserMixin


class DynamicFieldAdminChoicesFormView(RequireSuperuserMixin, TemplateView):
    template_name = 'cosinnus/dynamic_fields/dynamic_field_form.html'
    form_generator_class = DynamicFieldAdminChoicesFormGenerator

    def get(self, request, *args, **kwargs):
        generator = self.form_generator_class(cosinnus_portal=CosinnusPortal.get_current())
        self.forms = generator.get_forms()

        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        generator = self.form_generator_class(cosinnus_portal=CosinnusPortal.get_current(), data=request.POST)
        self.forms = generator.get_forms()

        generator.try_save()
        if generator.saved:
            messages.success(self.request, _('Your data was saved successfully!'))
            return redirect(self.request.path)
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(DynamicFieldAdminChoicesFormView, self).get_context_data(**kwargs)
        context.update(
            {
                'forms': self.forms,
            }
        )
        return context


dynamic_field_admin_choices_form_view = DynamicFieldAdminChoicesFormView.as_view()
