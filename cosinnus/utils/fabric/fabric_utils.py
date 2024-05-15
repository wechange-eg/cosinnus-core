import functools

from django.core.exceptions import ImproperlyConfigured
from fabric import Connection, task

# the env used for all cosinnus fabric connections
_env = None


class CosinnusFabricConnection(Connection):
    """Wrapper for the fabric Connection object that prints commands to stdout
    as they are being executed."""

    def run(self, *args, **kwargs):
        print(f'>>> run\t {args[0]}\n')
        return super().run(*args, **kwargs)

    def cd(self, *args, **kwargs):
        print(f'cd:\t {args[0]}')
        return super().cd(*args, **kwargs)

    def prefix(self, *args, **kwargs):
        print(f'with:\t {args[0]}')
        return super().prefix(*args, **kwargs)


def cosinnus_fabric_task(func, **kwargs):
    """
    Wrapper for fabric.task that prints out the task about to execute to stdout.
    """
    func_name = func.__name__

    @functools.wraps(func)
    def wrapper(ctx, **kwargs):
        print(f'\n##########  Task: {func_name}  ##########\n')
        return func(ctx, **kwargs)

    return task(wrapper, **kwargs)


class _AttributeDict(dict):
    """
    Dictionary subclass enabling attribute lookup/assignment of keys/values.
    Taken over from fabric 1.*

    For example::

        >>> m = _AttributeDict({'foo': 'bar'})
        >>> m.foo
        'bar'
        >>> m.foo = 'not bar'
        >>> m['foo']
        'not bar'

    ``_AttributeDict`` objects also provide ``.first()`` which acts like
    ``.get()`` but accepts multiple keys as arguments, and returns the value of
    the first hit, e.g.::

        >>> m = _AttributeDict({'foo': 'bar', 'biz': 'baz'})
        >>> m.first('wrong', 'incorrect', 'foo', 'biz')
        'bar'

    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            # to conform with __getattr__ spec
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def first(self, *names):
        for name in names:
            value = self.get(name)
            if value:
                return value


def get_env():
    """Returns the env used for all cosinnus fabric connections"""
    global _env
    if _env is None:
        _env = _AttributeDict({})
    return _env


def setup_env(
    portal_name,
    domain,
    pull_branch,
    cosinnus_pull_branch,
    confirm=False,
    base_path=None,
    pull_remote='origin',
    cosinnus_pull_remote='origin',
    frontend_pull_branch='main',
    frontend_pull_remote='origin',
    legacy_mode=False,
    special_requirements='requirements-production.txt',
    new_unit_commands=False,
):
    """
    Sets up the env with all variables needed to run cosinnus
    fabric commands.
    @param portal_name: the name for the user and portal instance
    @param domain: the URL domain for the portal, for SSH connections and
        on-server paths
    @param pull_branch: the branch that the main repo will be pulled from
    @param cosinnus_pull_branch: the branch that the cosinnus repo will be pulled from on updates
        (see `hotdeploy()` for further explanations)
    @param base_path: if the on-server file location path for the portal
        is non-default, use this argument to override it
    @param pull_remote: used to override non-origin git pulls
    @param cosinnus_pull_remote: used to override non-origin git pulls for the cosinnus-core repo
    @param legacy_mode: set this to True for deploys on portals that
        do not have the v3 redesign devops architecture yet (pip instead of poetry, etc)
    @param special_requirements: if run in `legacy_mode == True`, this can be used to change
        the requirements file
    @param new_unit_commands: set to True to use the newer, unified configuration for unit commands.
    """
    if not base_path and domain:
        base_path = f'/srv/http/{domain}'
    # if not base_path:
    #    raise ImproperlyConfigured('`setup_env()` did not receive all necessary arguments!')

    env = get_env()
    env.portal_name = portal_name
    env.username = portal_name
    env.host = f'{portal_name}@{domain}'
    env.path = f'{base_path}/htdocs'
    env.frontend_path = f'{base_path}/frontend'
    env.virtualenv_path = f'{env.path}/.venv'
    env.cosinnus_src_path = f'{env.virtualenv_path}/src/cosinnus'
    if not legacy_mode:
        env.cosinnus_src_path = f'{env.virtualenv_path}/src/cosinnus-core'
    env.backup_path = f'{base_path}/backups'
    env.maintenance_mode_path = base_path
    env.pull_branch = pull_branch
    env.pull_remote = pull_remote
    env.cosinnus_pull_branch = cosinnus_pull_branch
    env.cosinnus_pull_remote = cosinnus_pull_remote
    env.frontend_pull_branch = frontend_pull_branch
    env.frontend_pull_remote = frontend_pull_remote
    env.lessc_binary = '~/node_modules/.bin/lessc'
    env.skip_compile_webpack = bool(not legacy_mode)

    env.memcached_restart_command = f'sudo /bin/systemctl restart django-{portal_name}-memcached.service'
    env.frontend_restart_command = f'sudo systemctl restart django-{portal_name}-node-frontend.service'
    if not legacy_mode:
        env.lessc_binary = f'{env.cosinnus_src_path}/node_modules/.bin/lessc'
    if legacy_mode:
        env.reload_command = f'sudo /bin/systemctl restart django-{portal_name}.service'
        env.stop_command = f'sudo /bin/systemctl stop django-{portal_name}.service'
        env.start_command = f'sudo /bin/systemctl start django-{portal_name}.service'
    elif new_unit_commands:
        env.reload_command = f'sudo /bin/systemctl restart portal-{portal_name}-django.service'
        env.stop_command = f'sudo /bin/systemctl stop portal-{portal_name}-django.service'
        env.start_command = f'sudo /bin/systemctl start portal-{portal_name}-django.service'
        env.memcached_restart_command = f'sudo /bin/systemctl restart portal-{portal_name}-memcached.service'
        env.frontend_restart_command = f'sudo /bin/systemctl restart portal-{portal_name}-frontend.service'
        # or maybe this, even newer?
        # env.frontend_restart_command = f'sudo /bin/systemctl restart django-{portal_name}-node-frontend.service'
    else:
        env.reload_command = 'sudo systemctl restart unit-config.service'
        env.stop_command = 'sudo systemctl stop unit-config.service'  # there is no stop for the unit-config, only for the config-service
        env.start_command = 'sudo systemctl restart unit-config.service'  # this is why here we restart the unit config, so all gets restarted after stopping

    env.portal_additional_less_to_compile = []  # a list of django apps for which to compile extra less
    env.db_name = portal_name
    env.db_username = portal_name
    env.confirm = confirm
    env.legacy_mode = False

    if legacy_mode:
        env.legacy_mode = True
        env.virtualenv_path = f'{base_path}/venv'
        env.special_requirements = special_requirements
    return env
