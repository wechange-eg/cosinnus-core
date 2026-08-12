from rest_framework import serializers

from cosinnus.models.personal_dashboard import (
    get_personal_dashboard_widget,
    get_personal_dashboard_widget_ids,
    get_personal_dashboard_widgets,
)
from cosinnus.models.user_dashboard_announcement import UserDashboardAnnouncement, UserDashboardCallToActionButton


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


class CosinnusPersonalDashboardAnnouncementCallToActionButtonSerializer(serializers.ModelSerializer):
    """Serializer for dashboard announcement call-to-action buttons."""

    class Meta:
        model = UserDashboardCallToActionButton
        fields = (
            'label',
            'url',
        )


class CosinnusPersonalDashboardAnnouncementSerializer(serializers.ModelSerializer):
    """Serializer for the dashboard usr announcements."""

    id = serializers.IntegerField()
    category = serializers.CharField(source='get_category_display', read_only=True)
    cta_buttons = CosinnusPersonalDashboardAnnouncementCallToActionButtonSerializer(
        source='call_to_action_buttons', many=True
    )
    dismissed = serializers.BooleanField(write_only=True)

    class Meta:
        model = UserDashboardAnnouncement
        fields = (
            'id',
            'title',
            'category',
            'display',
            'image',
            'text',
            'text_col_1',
            'text_col_2',
            'cta_buttons',
            'dismissed',
        )

    def validate(self, attrs):
        # check widget id is valid
        announcement_id = attrs.get('id')
        if not announcement_id:
            raise serializers.ValidationError({'id': 'This field is required.'})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # handle "none" category type
        if instance.category == 0:
            data['category'] = None

        # reset image and text field depending on display option
        if instance.display == UserDashboardAnnouncement.DISPLAY_IMAGE_AND_TEXT:
            data['text_col_1'] = None
            data['text_col_2'] = None
        else:
            data['image'] = None
            data['text'] = None
        return data


class CosinnusPersonalDashboardSerializer(serializers.Serializer):
    """Serializer for the v3 personal dashboard."""

    widgets = CosinnusPersonalDashboardWidgetSerializer(many=True)
    announcement = CosinnusPersonalDashboardAnnouncementSerializer()

    def __init__(self, instance=None, context=None, **kwargs):
        if 'data' not in kwargs and context:
            # initialize using widgets
            user = context['user']
            widgets = [widget for widget in get_personal_dashboard_widgets() if widget.is_enabled(user)]
            preview_announcement_id = context['query_params'].get('show_announcement')
            if preview_announcement_id:
                announcement = UserDashboardAnnouncement.objects.filter(pk=preview_announcement_id).first()
            else:
                announcement = UserDashboardAnnouncement.get_next_for_user(user)
            instance = {'widgets': widgets, 'announcement': announcement}
        super().__init__(instance, context=context, **kwargs)

    def save(self, **kwargs):
        user = self.context['user']

        # save widget settings for user
        widgets_data = self.validated_data.get('widgets', [])
        for widget_data in widgets_data:
            widget = get_personal_dashboard_widget(widget_data['id'])
            if 'active' in widget_data:
                widget.set_active(user, widget_data['active'])
            if 'display' in widget_data:
                widget.set_display(user, widget_data['display'])

        # handle dismissing an announcement
        announcement_data = self.validated_data.get('announcement')
        if announcement_data and announcement_data['dismissed']:
            UserDashboardAnnouncement.hide_next_for_user(user, announcement_data['id'])
