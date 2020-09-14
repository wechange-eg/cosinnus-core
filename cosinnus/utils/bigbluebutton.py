from cosinnus.models import CosinnusGroupMembership, BBBRoom
from django.db.models import Q


def update_bbbroom_membership(sender, instance, signal, created, *args, **kwargs):
    rooms = BBBRoom.objects.filter(
        Q(attendees__id__in=[instance.user.id]) |
        Q(moderators__id__in=[instance.user.id]) |
        Q(group=instance.membership.group)
    )

    for room in rooms:
        room.join_user(instance.user)

