from rest_framework import serializers

# Choices for the DeckEventSerializer type field
DECK_EVENT_TYPE_TASK_CREATED = 'nc_deck_task_created'
DECK_EVENT_TYPE_TASK_STATUS_CHANGED = 'nc_deck_task_status_changed'
DECK_EVENT_TYPE_TASK_DUE_DATE_CHANGED = 'nc_deck_task_duedate_changed'
DECK_EVENT_TYPE_TASK_ASSIGNEE_CHANGED = 'nc_deck_task_assignee_changed'
DECK_EVENT_TYPE_TASK_COMMENT_CREATED = 'nc_deck_task_comment_created'
DECK_EVENT_TYPE_TASK_USER_MENTIONED = 'nc_deck_user_mentioned'
DECK_EVENT_TYPE_TASK_DELETED = 'nc_deck_task_deleted'
DECK_EVENT_TYPE_CHOICES = [
    (DECK_EVENT_TYPE_TASK_CREATED, DECK_EVENT_TYPE_TASK_CREATED),
    (DECK_EVENT_TYPE_TASK_STATUS_CHANGED, DECK_EVENT_TYPE_TASK_STATUS_CHANGED),
    (DECK_EVENT_TYPE_TASK_DUE_DATE_CHANGED, DECK_EVENT_TYPE_TASK_DUE_DATE_CHANGED),
    (DECK_EVENT_TYPE_TASK_ASSIGNEE_CHANGED, DECK_EVENT_TYPE_TASK_ASSIGNEE_CHANGED),
    (DECK_EVENT_TYPE_TASK_COMMENT_CREATED, DECK_EVENT_TYPE_TASK_COMMENT_CREATED),
    (DECK_EVENT_TYPE_TASK_USER_MENTIONED, DECK_EVENT_TYPE_TASK_USER_MENTIONED),
    (DECK_EVENT_TYPE_TASK_DELETED, DECK_EVENT_TYPE_TASK_DELETED),
]


# Choices for the DeckFollowSerializer type field
DECK_FOLLOW_TYPE_CHOICES = [
    ('card', 'card'),
]


class DeckStackSerializer(serializers.Serializer):
    title = serializers.CharField()
    order = serializers.IntegerField()


class DeckLabelSerializer(serializers.Serializer):
    title = serializers.CharField()
    color = serializers.CharField()


class DeckEventSerializer(serializers.Serializer):
    """
    Basic required fields in all events.
    The type values is used to load the serializer for the enent, see get_get_deck_event_serializer below.
    """

    type = serializers.ChoiceField(choices=DECK_EVENT_TYPE_CHOICES)
    id = serializers.CharField()
    requestUserId = serializers.CharField()


class DeckTaskDataSerializer(serializers.Serializer):
    """Basic fields required in the data field of all task events."""

    boardId = serializers.IntegerField()
    taskId = serializers.IntegerField()
    taskTitle = serializers.CharField()


class DeckTaskEventSerializer(DeckEventSerializer):
    """Basic task event serializer."""

    data = DeckTaskDataSerializer()


class DeckTaskStatusDataSerializer(DeckTaskDataSerializer):
    """Data of the status changed event."""

    done = serializers.BooleanField()


class DeckTaskStatusChangedEventSerializer(DeckEventSerializer):
    """Status changed event serializer."""

    data = DeckTaskStatusDataSerializer()


class DeckTaskDueDateDataSerializer(DeckTaskDataSerializer):
    """Data of the due date changed event."""

    duedate = serializers.DateTimeField()


class DeckTaskDueDateChangedEventSerializer(DeckEventSerializer):
    """Due date changed event seriolizer."""

    data = DeckTaskDueDateDataSerializer()


class DeckTaskAssigneeDataSerializer(DeckTaskDataSerializer):
    """Data of the assignee changed event."""

    userId = serializers.CharField()
    assigned = serializers.BooleanField()


class DeckTaskAssigneeChangedEventSerializer(DeckEventSerializer):
    """Assignee changed event serializer."""

    data = DeckTaskAssigneeDataSerializer()


class DeckTaskCommentCreatedDataSerializer(DeckTaskDataSerializer):
    """Data of the comment created event."""

    mentions = serializers.ListField(child=serializers.CharField())


class DeckTaskCommentCreatedEventSerializer(DeckEventSerializer):
    """Comment created event serializer."""

    data = DeckTaskCommentCreatedDataSerializer()


class DeckTaskMentionDataSerializer(DeckTaskDataSerializer):
    """Data of the user mentioned event."""

    userId = serializers.CharField()


class DeckTaskUserMentionedEventSerializer(DeckEventSerializer):
    """User mentioned event serializer."""

    data = DeckTaskMentionDataSerializer()


def get_deck_event_serializer(event_type, data):
    """Helper to get the serialized data for a specific event type."""
    serializer_by_type = {
        DECK_EVENT_TYPE_TASK_CREATED: DeckTaskEventSerializer,
        DECK_EVENT_TYPE_TASK_STATUS_CHANGED: DeckTaskStatusChangedEventSerializer,
        DECK_EVENT_TYPE_TASK_DUE_DATE_CHANGED: DeckTaskDueDateChangedEventSerializer,
        DECK_EVENT_TYPE_TASK_ASSIGNEE_CHANGED: DeckTaskAssigneeChangedEventSerializer,
        DECK_EVENT_TYPE_TASK_COMMENT_CREATED: DeckTaskCommentCreatedEventSerializer,
        DECK_EVENT_TYPE_TASK_USER_MENTIONED: DeckTaskUserMentionedEventSerializer,
        DECK_EVENT_TYPE_TASK_DELETED: DeckTaskEventSerializer,
    }
    serializer = serializer_by_type[event_type]
    return serializer(data=data)


class DeckFollowSerializer(serializers.Serializer):
    """Serializer for follow requests. NOTE: type currently allows only cards."""

    type = serializers.ChoiceField(choices=DECK_FOLLOW_TYPE_CHOICES)
    id = serializers.IntegerField()
    follow = serializers.BooleanField()
