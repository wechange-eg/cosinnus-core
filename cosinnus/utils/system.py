import os
import sys
import environ

from django.core.management import execute_from_command_line

# test parameters
TEST_ROCKET_CHAT_ARG = "--test-rocketchat"
TEST_BBB_CHAT_ARG = "--test-bbb"
TEST_PRINT_TIME_ARG = "--print-time"

# test apps
TEST_APPS_BASE = ['cosinnus', 'cosinnus_event', 'cosinnus_todo']
TEST_APPS_ROCKET_CHAT = ['cosinnus.tests.test_rocketchat']
TEST_APPS_BBB = ['cosinnus.tests.test_bbb']


def cosinnus_manage(base_path):
    """
    Manage command with custom .env file, settings and test handling.
    Loads the variables in .env (.env.test when running tests) into the environment.
    Sets the settings module to the one set in WECHANGE_DJANGO_SETTINGS_MODULE during normal runs.
    During test runs custom settings are used from cosinnus.tests.settings depending on the test arguments.
    Arguments:
    --test-rocketchat:  Run RocketChat service tests.
    --test-bbb:         Run BBB service tests.
    --print-time:       Prints execution time for slow test (>0.5s).
    """

    args = list(sys.argv)
    env = environ.Env()

    is_test_run = "test" in sys.argv

    # read env file
    env_file = ".env" if not is_test_run else ".env.test"
    env_file_path = base_path(env_file)
    if not os.path.exists(env_file_path):
        print(f'Could not load env file {env_file_path}!')
        exit()
    env.read_env(env_file_path)

    if not is_test_run:
        # set the settings module.
        try:
            settings_module = env("WECHANGE_DJANGO_SETTINGS_MODULE")
        except environ.ImproperlyConfigured:
            print("Misconfigured: The entrypoint settings module 'WECHANGE_DJANGO_SETTINGS_MODULE' was not found in'.env'! Example: 'WECHANGE_DJANGO_SETTINGS_MODULE=config.settings.staging'.")
            raise
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    else:
        # Testing improvements

        # handle test parameters.
        custom_test = any('.tests.' in arg for arg in args)
        settings_module = "cosinnus.tests.settings.test"
        if TEST_ROCKET_CHAT_ARG in args:
            settings_module = "cosinnus.tests.settings.test_rocketchat"
            if not custom_test:
                args.extend(TEST_APPS_ROCKET_CHAT)
            args.remove(TEST_ROCKET_CHAT_ARG)
        elif TEST_BBB_CHAT_ARG in args:
            settings_module = "cosinnus.tests.settings.test_bbb"
            custom_test = any('.tests.' in arg for arg in args)
            if not custom_test:
                args.extend(TEST_APPS_BBB)
            args.remove(TEST_ROCKET_CHAT_ARG)
        elif not custom_test:
            args.extend(TEST_APPS_BASE)
        os.environ["DJANGO_SETTINGS_MODULE"] = settings_module

        if TEST_PRINT_TIME_ARG in args:
            # Print execution times of slow tests.
            from django import test
            import time

            def setUp(self):
                self.startTime = time.time()

            def tearDown(self):
                total = time.time() - self.startTime
                if total > 0.5:
                    print("\n\t\033[91m%.3fs\t%s\033[0m" % (total, self._testMethodName))

            test.TestCase.setUp = setUp
            test.TestCase.tearDown = tearDown

            args.remove(TEST_PRINT_TIME_ARG)

    execute_from_command_line(args)