Services Integration
====================

Cosinnus includes integration with various callaboration services.

NextCloud
---------

An admin user needs to be created in NextCloud that is used by Cosinnus to access the API.

To enable NextCloud add the following settings to the portal settings::

    COSINNUS_CLOUD_ENABLED = True

Optionally you can adjust the cloud URL and admin user name::

    COSINNUS_CLOUD_NEXTCLOUD_URL = "<url>"  # default: https://cloud.<portal-url>
    COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME = "<username>"  # default: admin

Finally provide the password of the admin in the portal `.env` file::

    WECHANGE_COSINNUS_CLOUD_PASSWORD=<password>

NextCloud can be accessed via the navbar. It can be also enabled for a group in the group settings and will be
integrated on the group dashboard.

RocketChat
----------

An admin user needs to be created in RocketChat that is used by Cosinnus to access the API.

To enable RocketChat add the following settings to the portal settings::

    COSINNUS_ROCKET_ENABLED = True

Optionally you can adjust the cloud URL and admin user name::

    COSINNUS_CHAT_BASE_URL = "<url>"  # default: https://chat.<portal-url>
    COSINNUS_CHAT_USER = "<user>"  # default: <portal-name>-bot

Finally provide the password of the admin in the portal `.env` file::

    WECHANGE_COSINNUS_CHAT_PASSWORD=<password>

RocketChat can be accessed via the navbar. It can be also enabled for a group in the group settings and will be
integrated on the group dashboard.

BigBlueButton
-------------

BigBlueButton integration can be enabled in the portal settings via::

    COSINNUS_CONFERENCES_ENABLED = True

This will allow you to create conferences.

To allow non admin users to create conferences add::

    COSINNUS_USERS_CAN_CREATE_CONFERENCES = True

Additionally BBB can be added to groups and events via::

    COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS = True
    COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED = False

After this you well be able to add a BBB conference to a group or event in the settings form. For groups this will add a
conference link to the group dashboard. For events it will add a conference link to the event detail page.

Fairmeeting
-----------

As an alternative to BBB, groups and events can also have a Fairmeeting conference. It can be enabled by setting the
server URL in the portal settings in the Django Admin.

Etherpad / Ethercalc
--------------------

Etherpad and Ethercalc integration is enabled per default. The server urls can be adjusted in the portal settings::

    COSINNUS_ETHERPAD_BASE_URL = "<url>"  # default: "https://pad.<poral-url>/api"
    COSINNUS_ETHERPAD_ETHERCALC_BASE_URL = "<url"  # default: "https://calc.<portal-url>"

In addition you need to set the API key in the portal `.env` file::

    WECHANGE_COSINNUS_ETHERPAD_API_KEY=<key>

When configured the etherpad app can be enabled for a group in the group settings.

Inter-Portal-Exchange
---------------------

The inter-portal-exchange feature makes groups, projects and events of a portal available in the map view of other portals.
This is done by adding the groups to the ElasticSearch search index of a portal.

The inter-portal-exchange can be configured in the portal settings::

    COSINNUS_EXCHANGE_ENABLED = True
    COSINNUS_EXCHANGE_RUN_EVERY_MINS = 60*24 # once a day
    COSINNUS_EXCHANGE_BACKENDS = [
        {
            'backend': 'cosinnus_exchange.backends.ExchangeBackend',
            'url': 'https://<other-portal-url>/api/v2/events/',
            'source': '<other-portal-name>',
            'model': 'cosinnus_exchange.ExchangeEvent',
            'serializer': 'cosinnus_exchange.serializers.ExchangeEventSerializer',
        },
        {
            'backend': 'cosinnus_exchange.backends.ExchangeBackend',
            'url': 'https://<other-portal-url>/api/v2/projects/',
            'source': '<other-portal-name>',
            'model': 'cosinnus_exchange.ExchangeProject',
            'serializer': 'cosinnus_exchange.serializers.ExchangeGroupSerializer',
        },
        {
            'backend': 'cosinnus_exchange.backends.ExchangeBackend',
            'url': 'https://<other-portal-url>/api/v2/groups/',
            'source': '<other-portal-name>',
            'model': 'cosinnus_exchange.ExchangeSociety',
            'serializer': 'cosinnus_exchange.serializers.ExchangeGroupSerializer',
        },
    ]

The import is done with a cron job task. To sync locally run::

     ./manage.py runcrons --force

After the sync the other portals content is searchable in the map / discover view.
