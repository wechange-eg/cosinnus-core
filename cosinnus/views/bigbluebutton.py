from cosinnus.models import BBBRoom


def bbb_meetings(request, group_id):
    rooms = BBBRoom.objects.filter(conference__group__id=group_id)
    return list(rooms)
