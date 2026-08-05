from rest_framework import serializers

from cosinnus.views.feedback import submit_report


class CosinnusReportSerializer(serializers.Serializer):
    """Serializer for complaint reports."""

    object_id = serializers.IntegerField(required=True)
    text = serializers.CharField(required=True)

    # target model class passed via init
    model_cls = None

    def __init__(self, **kwargs):
        self.model_cls = kwargs.pop('model_cls', None)
        super().__init__(**kwargs)

    def create(self, validated_data):
        request = self.context['request']
        object_id = validated_data['object_id']
        text = validated_data['text']
        return submit_report(request, self.model_cls, object_id, text)
