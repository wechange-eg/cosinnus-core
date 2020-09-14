from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from cosinnus.models import BBBRoom
from cosinnus.apis import bigbluebutton as bbb


def bbb_meetings(request, group_id):
    rooms = BBBRoom.objects.filter(conference__group__id=group_id)
    return list(rooms)


def join_meeting(request, meeting_id):
    if request.user:
        try:
            room = BBBRoom.objects.get(meeting_id=meeting_id)
            password = room.get_password_for_user(request.user)
            redirect_url = bbb.join_url(room.meeting_id, request.user.full_name, password)
            return redirect_url
        except ObjectDoesNotExist:
            return HttpResponse("Room not found")
    else:
        return HttpResponse("Insufficient user rights.")
