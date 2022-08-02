from django.forms import ModelMultipleChoiceField

from cosinnus.templatetags.cosinnus_tags import full_name


class UserNameModelMultipleChoiceField(ModelMultipleChoiceField):
    """
    Provides an oppurtunity to workaround the `ModelMultipleChoiceField`'s limitation 
    ragarding the usage of user names instead of user ids
    """
    def label_from_instance(self, obj):
        return full_name(obj)
