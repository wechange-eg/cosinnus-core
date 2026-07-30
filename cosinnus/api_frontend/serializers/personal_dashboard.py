from rest_framework import serializers

from cosinnus.models.personal_dashboard import (
    get_personal_dashboard_widget,
    get_personal_dashboard_widget_ids,
    get_personal_dashboard_widgets,
)


class CosinnusPersonalDashboardWidgetSerializer(serializers.Serializer):
    """Serializer for the v3 personal dashboard widgets."""

    id = serializers.CharField()
    active = serializers.BooleanField(required=False)
    display = serializers.JSONField(required=False)
    api_url = serializers.URLField(read_only=True)
    data = serializers.JSONField(read_only=True)
    conf = serializers.JSONField(read_only=True)

    def validate(self, attrs):
        # check widget id is valid
        widget_id = attrs.get('id')
        if not widget_id:
            raise serializers.ValidationError({'id': 'This field is required.'})
        elif widget_id not in get_personal_dashboard_widget_ids():
            raise serializers.ValidationError({'id': 'Unknown widget id.'})
        return attrs

    def to_representation(self, instance):
        user = self.context['user']
        ret = super().to_representation(instance)
        # populate user related fields from the widget
        ret.update(
            {
                'active': instance.is_active(user),
                'display': instance.get_display(user),
                'data': instance.get_data(user),
                'conf': instance.get_conf(user),
            }
        )
        return ret


class CosinnusPersonalDashboardSerializer(serializers.Serializer):
    """Serializer for the v3 personal dashboard."""

    widgets = CosinnusPersonalDashboardWidgetSerializer(many=True)

    def __init__(self, instance=None, context=None, **kwargs):
        if 'data' not in kwargs and context:
            # initialize using widgets
            user = context['user']
            instance = {'widgets': [widget for widget in get_personal_dashboard_widgets() if widget.is_enabled(user)]}
        super().__init__(instance, context=context, **kwargs)

    def save(self, **kwargs):
        user = self.context['user']
        # save widget settings for user
        widgets_data = self.validated_data.get('widgets')
        for widget_data in widgets_data:
            widget = get_personal_dashboard_widget(widget_data['id'])
            if 'active' in widget_data:
                widget.set_active(user, widget_data['active'])
            if 'display' in widget_data:
                widget.set_display(user, widget_data['display'])
