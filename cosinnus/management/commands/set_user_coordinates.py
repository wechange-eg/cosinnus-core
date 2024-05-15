from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from geopy.geocoders import Nominatim

from cosinnus.models import TagObject

User = get_user_model()


class GeoException(Exception):
    pass


class Command(BaseCommand):
    help = 'This command sets the coordinates of all users which have a location but no coordinates given'

    geolocator = None

    def add_arguments(self, parser):
        parser.add_argument('geolocator', type=str, help='The address of a nominatim server')

    def handle(self, *args, **kwargs):
        self.geolocator = Nominatim(domain=kwargs['geolocator'], user_agent='wechange')
        queryset = User.objects.filter(
            cosinnus_profile__media_tag__location_lat__isnull=True,
            cosinnus_profile__media_tag__location_lon__isnull=True,
            cosinnus_profile__media_tag__location__isnull=False,
        )

        count = 0
        errors = []
        for i, user in enumerate(queryset[:100]):
            self.stdout.write(f'Find user {i}/{queryset.count()}', ending='\r')
            self.stdout.flush()
            try:
                result = self.set_user_location(user)
                if result:
                    count += 1
            except GeoException as e:
                errors.append([i, str(e)])
        for i, error in errors:
            self.stderr.write(f'User {i}: {error}')
        self.stdout.write(f'Updated {count} users. Encountered {len(errors)} errors.')

    def _get_address(self, user):
        if hasattr(user, 'cosinnus_profile') and hasattr(user.cosinnus_profile, 'media_tag'):
            return user.cosinnus_profile.media_tag.location
        return

    def _find_address(self, address):
        location = self.geolocator.geocode(address, timeout=60)
        # If not found, try just with street and postal code
        if not location:
            street_postal_code = ', '.join(filter(None, address[:2]))
            location = self.geolocator.geocode(street_postal_code, timeout=60)
        if not location:
            return
        return (address, location.latitude, location.longitude)

    def set_user_location(self, user, dry_run=False):
        address = self._get_address(user)
        if not address:
            return False
        location = self._find_address(address)
        if isinstance(location, (tuple, list)):
            tag_object = TagObject(location=location[0], location_lat=location[1], location_lon=location[2])
            if not dry_run:
                tag_object.save()
            profile = user.cosinnus_profile
            profile.media_tag = tag_object
            if not dry_run:
                profile.save()
        elif isinstance(location, str):
            raise GeoException(f'{location}. Skipping user.')
        else:
            address_string = ', '.join(address)
            raise GeoException(f"Coudn't find address: {address_string}. Skipping user.")
        return True
