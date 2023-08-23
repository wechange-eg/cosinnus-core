import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models.query_utils import Q
from django.http.response import HttpResponseNotAllowed, HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic.list import ListView
from cosinnus import cosinnus_notifications

from cosinnus.conf import settings
from cosinnus.default_settings import LOGIN_URL
from cosinnus.models.profile import get_user_profile_model, UserMatchObject
from cosinnus.models.tagged import LikeObject
from cosinnus.utils.functions import is_number
from cosinnus.utils.permissions import check_user_can_see_user
from cosinnus.utils.user import filter_active_users
from datetime import timedelta
from django.utils.timezone import now


logger = logging.getLogger('cosinnus')


class UserMatchListView(LoginRequiredMixin, ListView):
    model = get_user_profile_model()
    template_name = 'cosinnus/user/user_match_list.html'
    login_url = LOGIN_URL

    def get_hashset_likes_for_user(self, user):
        """
        Get all the objects liked by a certain user.

        Args:
            user: UserObject.

        Returns:
            set(): Set of objects liked by the given user in form {content_type: object_id}
        """
        values_liked = LikeObject.objects.filter(user=user, liked=True).values_list('content_type', 'object_id')
        user_liked_set = set(f'{liketuple[0]}::{liketuple[1]}' for liketuple in values_liked)
        return user_liked_set

    # TODO: cache after!
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # exclude self
        user_profiles = self.model.objects.exclude(user=self.request.user)

        # filter only users I haven't liked or disliked yet
        already_liked_users = UserMatchObject.objects.filter(
            from_user=self.request.user, 
            type__in=[UserMatchObject.LIKE, UserMatchObject.DISLIKE]
        ).values_list('to_user_id', flat=True)
        user_profiles = user_profiles.exclude(user_id__in=already_liked_users)

        # filter out users that did not like me
        disliked_by_users = UserMatchObject.objects.filter(
            to_user=self.request.user, type=UserMatchObject.DISLIKE
        ).values_list('from_user_id', flat=True)
        user_profiles = user_profiles.exclude(user_id__in=disliked_by_users)

        # filter active users
        user_profiles = filter_active_users(user_profiles, filter_on_user_profile_model=True)

        # filter users for their profile visibility
        users = get_user_model().objects.filter(cosinnus_profile__in=user_profiles)
        checked_for_visibility_users = [user for user in users if check_user_can_see_user(self.request.user, user)]
        user_profiles = get_user_profile_model().objects.filter(user_id__in=checked_for_visibility_users)

        # filter user to be active within the last year
        last_year = now() - timedelta(days=365) # timedelta to pass users who have logged in at least once within the last year;
        user_profiles = user_profiles.filter(user__last_login__gte=last_year)

        request_user_liked_set = self.get_hashset_likes_for_user(self.request.user)
        score_dict = {}
        
        for profile in user_profiles:
            score = 0
            # profile fields score
            if profile.description and len(profile.description) > 10:
                score += 1
            if profile.avatar:
                score += 1
            if profile.website:
                score += 1
            if profile.email_verified:
                score += 1
            if profile.dynamic_fields:
                for field, value in profile.dynamic_fields.items():
                    if value:
                        score += 1
                        user_value = self.request.user.cosinnus_profile.dynamic_fields.get(field)
                        if user_value:
                            if isinstance(value, list):
                                score += len(set(user_value).intersection(set(value)))
                            elif user_value == value:
                                score += 1
            if profile.media_tag.topics:
                score += 1
                if profile.media_tag.topics == self.request.user.cosinnus_profile.media_tag.topics:
                    score += 1

            # score users active in the last month
            last_month = now() - timedelta(days=31)
            if profile.user.last_login > last_month:
                score += 1

            # mutual likes score
            this_user_liked_set = self.get_hashset_likes_for_user(profile.user)
            set_intersection = this_user_liked_set.intersection(request_user_liked_set)
            shared_like_count = len(set_intersection)
            score += shared_like_count
            
            score_dict[profile.id] = score

        score_dict = sorted(score_dict.items(), key=lambda score: score[1], reverse=True)
        result_score = {k: v for k, v in score_dict}

        selected_user_profiles = list(result_score.keys())[:3] # get first 3 user profiles with the highest counted score
        
        
        scored_user_profiles = self.model.objects.select_related('user').\
               filter(id__in=selected_user_profiles) # all active users related to the selected user profiles

        context.update({
            'scored_user_profiles': scored_user_profiles,
        })

        return context


def check_for_user_match(from_user, to_user):
    """ Checks if between two users, a MatchObject exists, in a way that both users
        "like" each other, and if so, triggers different effects. """
    try:
        match_case_from = UserMatchObject.objects.get(from_user=from_user, to_user=to_user, type=UserMatchObject.LIKE)
        match_case_to = UserMatchObject.objects.get(from_user=to_user, to_user=from_user, type=UserMatchObject.LIKE)
        
        # TODO: notification creation for matches disabled in current phase
        if False:
            # Create email notifications
            cosinnus_notifications.user_match_established.send(
                        sender=from_user,
                        obj=match_case_from,
                        user=from_user,
                        audience=[to_user,]
                    )
            
            cosinnus_notifications.user_match_established.send(
                        sender=to_user,
                        obj=match_case_to,
                        user=to_user,
                        audience=[from_user,]
                    )
        
        # open rocketchat
        if settings.COSINNUS_ROCKET_ENABLED:
            room_url = match_case_from.get_rocketchat_room_url()
            if match_case_from.rocket_chat_room_id and match_case_from.rocket_chat_room_name:
                match_case_to.rocket_chat_room_id = match_case_from.rocket_chat_room_id
                match_case_to.rocket_chat_room_name = match_case_from.rocket_chat_room_name
                match_case_to.save()
        else:
            logger.info('RocketChat is not enabled on this portal!')
    except UserMatchObject.DoesNotExist:
        pass


def match_create_view(request):
    """ 
    Creates an `UserMatchObject` where the `from_user` represents the current user, 
    `to_user` is certain user who got 'liked' or 'disliked', 
    and `action` is certain type of reaction which `to_user` got from `from_user`. 

    Args:
        request

    Raises:
        ValidationError: if `user_id` from POST.data is not an integer or is None;
        ValueError: if `action` from POST.data is not 'like', 'dislike' or 'ignore' or is None;
        ObjectDoesNotExist: if UserObject does not match the one with the given id;

    Returns:
        redirect: UserMatchListView
    """
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Not authenticated.')

    # check if `user_id` is a number
    user_id = request.POST.get('user_id')
    if user_id is None or not is_number(user_id):
        raise ValidationError(message=_('User id should be an integer and it should not be None.'))
    
    # check if `action` matches the given ones
    action = request.POST.get('action')
    if action is None or not int(action) in dict(UserMatchObject.TYPE_CHOICES).keys():
        raise ValueError(f'Action should be either "like", "dislike" or "ignore" and it should not be None.')

    # check if certain user exists
    user = get_user_model().objects.get(id=user_id)
    if not user or user is None:
        raise ObjectDoesNotExist('User matching query does not exist')
    
    # create `UserMatchObject`
    match_object, created = UserMatchObject.objects.get_or_create(from_user=request.user, to_user=user, defaults={'type': action})
    if not created and not match_object.type == action:
        match_object.type = action
        match_object.save()

    check_for_user_match(request.user, user)
    
    return redirect('cosinnus:user-match')



user_match_list_view = UserMatchListView.as_view()

