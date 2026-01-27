import os
import sys

import environ
from django.core.management import execute_from_command_line

# test parameters
TEST_ROCKET_CHAT_ARG = '--test-rocketchat'
TEST_BBB_ARG = '--test-bbb'
TEST_ETHERPAD_ARG = '--test-etherpad'
TEST_PAYMENTS_ARG = '--test-payments'
TEST_DECK_ARG = '--test-deck'
TEST_CALENDAR_ARG = '--test-calendar'
TEST_PRINT_TIME_ARG = '--print-time'

# test apps
TEST_APPS_BASE = ['cosinnus', 'cosinnus_event', 'cosinnus_todo']
TEST_APPS_ROCKET_CHAT = ['cosinnus.tests.test_rocketchat']
TEST_APPS_BBB = ['cosinnus.tests.test_bbbroom']
TEST_APPS_ETHERPAD = ['cosinnus_etherpad']
TEST_APPS_PAYMENTS = ['wechange_payments']
TEST_APPS_DECK = ['cosinnus.tests.test_deck']
TEST_APPS_CALENDAR = ['cosinnus.tests.test_calendar']

TEST_REQUIRED_ENV_SETTINGS = {
    'RocketChat': [
        'WECHANGE_COSINNUS_CHAT_BASE_URL',
        'WECHANGE_COSINNUS_CHAT_USER',
        'WECHANGE_COSINNUS_CHAT_PASSWORD',
    ],
    'BBB': [
        'WECHANGE_COSINNUS_BBB_SERVER_CHOICES',
        'WECHANGE_COSINNUS_BBB_SERVER_AUTH_AND_SECRET_PAIRS',
    ],
    'Etherpad': [
        'WECHANGE_COSINNUS_ETHERPAD_BASE_URL',
        'WECHANGE_COSINNUS_ETHERPAD_ETHERCALC_BASE_URL',
        'WECHANGE_COSINNUS_ETHERPAD_API_KEY',
    ],
    'Payments': [
        'WECHANGE_PAYMENTS_BETTERPAYMENT_API_KEY',
        'WECHANGE_PAYMENTS_BETTERPAYMENT_INCOMING_KEY',
        'WECHANGE_PAYMENTS_BETTERPAYMENT_OUTGOING_KEY',
        'WECHANGE_PAYMENTS_INVOICE_BACKEND_AUTH_DATA',
    ],
    'Deck': [
        'WECHANGE_COSINNUS_CLOUD_PASSWORD',
    ],
    'Calendar': [
        'WECHANGE_COSINNUS_CLOUD_PASSWORD',
        'WECHANGE_COSINNUS_BBB_SERVER_CHOICES',
        'WECHANGE_COSINNUS_BBB_SERVER_AUTH_AND_SECRET_PAIRS',
    ],
}


def _check_test_env_settings(env, service):
    """Checks that all required settings are set in .env.test for service tests."""
    service_settings_valid = True
    for setting in TEST_REQUIRED_ENV_SETTINGS[service]:
        try:
            env(setting)
        except environ.ImproperlyConfigured:
            print(f'{service} tests require "{setting}" to be set in ".env.test".')
            service_settings_valid = False
    if not service_settings_valid:
        exit()


def cosinnus_manage(base_path):
    """
    Manage command with custom .env file, settings and test handling.
    Loads the variables in .env (.env.test when running tests) into the environment.
    Sets the settings module to the one set in WECHANGE_DJANGO_SETTINGS_MODULE during normal runs.
    During test runs custom settings are used from cosinnus.tests.settings depending on the test arguments.
    The .env.test file needed for testing can be created by copying the .env file used for local development, with
    WECHANGE_HAYSTACK_INDEX_NAME adjusted to a dedicated test index. The service settings such as
    WECHANGE_COSINNUS_CHAT_* settings should be set to a service that can be used for testing.
    Arguments:
    --test-rocketchat:  Run RocketChat service tests.
    --test-bbb:         Run BBB service tests.
    --test-etherpad:    Run Etherpad/Ethercalc service tests.
    --test-payments:    Run wechange-payments tests.
    --test-deck:        Run deck app tests.
    --test-calendar:    Run calendar app tests.
    --print-time:       Prints execution time for slow test (>0.5s).
    """

    args = list(sys.argv)
    env = environ.Env()

    is_test_run = 'test' in sys.argv

    # read env file
    env_file = '.env' if not is_test_run else '.env.test'
    env_file_path = base_path(env_file)
    if not os.path.exists(env_file_path):
        print(f'Could not load env file {env_file_path}!')
        exit()
    env.read_env(env_file_path)

    if not is_test_run:
        # set the settings module.
        try:
            settings_module = env('WECHANGE_DJANGO_SETTINGS_MODULE')
        except environ.ImproperlyConfigured:
            print(
                "Misconfigured: The entrypoint settings module 'WECHANGE_DJANGO_SETTINGS_MODULE' was not found in "
                "'.env'! Example: 'WECHANGE_DJANGO_SETTINGS_MODULE=config.settings.staging'."
            )
            raise
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

    else:
        # Testing improvements

        # handle test parameters.
        custom_test = any('.tests.' in arg for arg in args)
        settings_module = 'cosinnus.tests.settings.test'
        if TEST_ROCKET_CHAT_ARG in args:
            _check_test_env_settings(env, 'RocketChat')
            settings_module = 'cosinnus.tests.settings.test_rocketchat'
            if not custom_test:
                args.extend(TEST_APPS_ROCKET_CHAT)
            args.remove(TEST_ROCKET_CHAT_ARG)
        elif TEST_BBB_ARG in args:
            _check_test_env_settings(env, 'BBB')
            settings_module = 'cosinnus.tests.settings.test_bbb'
            if not custom_test:
                args.extend(TEST_APPS_BBB)
            args.remove(TEST_BBB_ARG)
        elif TEST_ETHERPAD_ARG in args:
            _check_test_env_settings(env, 'Etherpad')
            settings_module = 'cosinnus.tests.settings.test_etherpad'
            if not custom_test:
                args.extend(TEST_APPS_ETHERPAD)
            args.remove(TEST_ETHERPAD_ARG)
        elif TEST_PAYMENTS_ARG in args:
            _check_test_env_settings(env, 'Payments')
            settings_module = 'cosinnus.tests.settings.test_payments'
            if not custom_test:
                args.extend(TEST_APPS_PAYMENTS)
            args.remove(TEST_PAYMENTS_ARG)
        elif TEST_DECK_ARG in args:
            _check_test_env_settings(env, 'Deck')
            settings_module = 'cosinnus.tests.settings.test_deck'
            if not custom_test:
                args.extend(TEST_APPS_DECK)
            args.remove(TEST_DECK_ARG)
        elif TEST_CALENDAR_ARG in args:
            _check_test_env_settings(env, 'Calendar')
            settings_module = 'cosinnus.tests.settings.test_calendar'
            if not custom_test:
                args.extend(TEST_APPS_CALENDAR)
            args.remove(TEST_CALENDAR_ARG)
        elif not custom_test:
            args.extend(TEST_APPS_BASE)
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_module

        if TEST_PRINT_TIME_ARG in args:
            # Print execution times of slow tests.
            import time

            from django import test

            def setUp(self):
                self.startTime = time.time()

            def tearDown(self):
                total = time.time() - self.startTime
                if total > 0.5:
                    print('\n\t\033[91m%.3fs\t%s\033[0m' % (total, self._testMethodName))

            test.TestCase.setUp = setUp
            test.TestCase.tearDown = tearDown

            args.remove(TEST_PRINT_TIME_ARG)

    execute_from_command_line(args)
