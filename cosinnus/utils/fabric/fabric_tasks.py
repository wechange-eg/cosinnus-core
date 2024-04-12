"""
    Cosinnus fabric tasks definitions.
    
    How to use: define a `fabfile.py` in your project with one task per target server. Example fabfile.py:
    
    ```
    from fabric import task
    from cosinnus.utils.fabric.fabric_utils import CosinnusFabricConnection, setup_env
    from cosinnus.utils.fabric.fabric_tasks import *
    
    @task
    def staging(_ctx):
        env = setup_env(
            portal_name='my_portal',
            domain='my_portal.de',
            pull_branch='my_branch',
        )
    ```
    
    Then invoke any task defined in this file by calling `fab`. 
    Usually you want to only call the high level tasks, (see "Deployment tasks" below),
    unless you want to chain individual small tasks to perform a custom execution.
    
    Examples:
    
    `fab staging hotdeploy` (fast deploy for small changes)
    
    `fab staging deploy` (proper deploy with downtime banner)
    
    `fab staging pull restart` (custom execution)
"""

from cosinnus.utils.fabric.fabric_utils import cosinnus_fabric_task as task
from cosinnus.utils.fabric.fabric_utils import get_env, CosinnusFabricConnection
from django.utils.crypto import get_random_string

# Sudo cd context https://stackoverflow.com/questions/50834162/in-fabric-2-invoke-change-directory-and-use-sudo
"""
# Normal task with cd
@task
def foo(context):
    with context.cd('/'):
        context.run('pwd')

"""

# virtualenv: https://stackoverflow.com/questions/53182539/conda-virtual-environment-with-fabric2
"""
@task(hosts=['servername'])
def do_things(c):
    with c.cd('your_dir'):
        # assuming you already added myenv to your path 
        with c.prefix('source activate myenv'): 
            c.run('pip3.6 install -r requirements.txt') #for example if you have

"""


""" ----------- Deployment tasks ----------- """

@task
def deploy(_ctx, do_maintenance=True):
    """ 
        Main deploy command, full deploy with dependency update, raising a downtime banner
        on the entire site, blocking any user access.
        
        Will do the following in order:
            * pull up a maintenance notice page
            * stop the servers
            * do a DB backup
            * pull from git
            * pip update
            * migrate
            * start the servers
            * remove the maintenance notice page 
    """
    check_confirmation()
    backup(_ctx)
    if do_maintenance:
        maintenanceon(_ctx)
    stop(_ctx)
    _pull_and_update()
    # restart_db()
    migrate(_ctx)
    start(_ctx)
    compilewebpack(_ctx)
    collectstatic(_ctx)
    compileless(_ctx)
    if do_maintenance:
        maintenanceoff(_ctx)

@task
def hotdeploy(_ctx):
    """ Fast deploy with poetry update and soft server restarts. No downtime-banner raised.
        Recommended only for hotfixes that do not require migrations,
        else you run the risk that active users get server errors while the deploy is running. """
    check_confirmation()
    _pull_and_update()
    migrate(_ctx)
    restart(_ctx)
    compilewebpack(_ctx)
    collectstatic(_ctx)
    compileless(_ctx)


@task
def fastdeploy(_ctx):
    """ Fast deploy with soft server restarts. No migrating or poetry update done."""
    fastpull(_ctx)
    restart(_ctx)
    collectstatic(_ctx)
    compileless(_ctx)


@task
def fastpull(_ctx):
    """ Only does a git pull on the base project repository """
    check_confirmation()
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.cd(env.path):
        c.run(f'git checkout {env.pull_branch}')
        c.run(f'git pull')
        
        
@task
def deployfrontend(_ctx):
    """ Only does a git pull on the base project repository """
    check_confirmation()
    _pull_and_update_frontend()
    restartfrontend(_ctx)
    

@task
def fulldeploy(_ctx):
    """ Deploys and forces a complete recreation of the virtual env. 
        This will require a complete django unit stop and will pull up a maintenance banner on the server.
        This will take longer and can be risky if the new build doesn't work. 
        
        This should only be done if some drastic architecture changes for poetry have happened or the 
        old environment is irrevocably broken (or also probably if poetry is again 
        just not updating its dependencies no matter what you try)."""
    
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    text = input(
        f'\n     **************   \n\n\tEXTRA\n\n\tWARNING!!!\n\n   ************* \n\nThis will do a complete deploy to the Server """{env.host}""", including a server stop, maintenance banner and DESTROY the poetry virtual env and CREATE IT FROM SCRATCH.\nIf you are sure you want this, type "YES" to continue: '
    )
    if not text == 'YES':
        print('Canceled deploy with resetting the virtualenv.')
        exit()
    
    check_confirmation()
    maintenanceon(_ctx)
    # move the old poetry.lock and virtualenv, forcing poetry to create them from scratch on install
    foldername = f'_DELETEME_moved_old_env_{get_random_string(length=6).lower()}'
    with c.cd(env.path):
        c.run(f'mkdir ~/{foldername}')
        c.run(f'mkdir -p .venv') # create if not exists
        c.run(f'mv .venv ~/{foldername}/movedvenv.venv')
        c.run(f'touch poetry.lock') # create if not exists
        c.run(f'mv poetry.lock ~/{foldername}/movedpoetry.lock')
    _pull_and_update(fresh_install=True)
    migrate(_ctx)
    restart(_ctx)
    compilewebpack(_ctx)
    collectstatic(_ctx)
    compileless(_ctx)
    maintenanceoff(_ctx)
    print('Note: this may fail if no redesign frontend is present yet for this portal. In that case, this is fine!')
    restartfrontend(_ctx)


""" ----------- Single helper tasks. Used in deploy tasks, but can also be called solo ----------- """

def check_confirmation():
    """ Blocks execution with a shell confirmation prompt """
    env = get_env()
    if env.confirm:
        text = input(
            f'\n     **************   WARNING!   ************* \n\nYou are about to deploy to the Server """{env.host}""".\nIf you are sure you want this, type "YES" to continue: '
        )
        if not text == 'YES':
            print('Canceled deploy.')
            exit()
    
@task
def restart(_ctx):
    """ Restart the django service """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    c.run(env.reload_command)
    
@task
def restartfrontend(_ctx):
    """ Restart the frontend node service """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    c.run(env.frontend_restart_command)

@task
def stop(_ctx):
    """ Stop the django service """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    c.run(env.stop_command)

@task
def start(_ctx):
    """ Start the django service """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    c.run(env.start_command)

@task
def restartmemcached(_ctx):
    """ Restart the django service """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    c.run(env.memcached_restart_command)

@task
def maintenanceon(_ctx):
    """ Turn on maintenance mode by moving the maintenance.html file
        where nginx will see it and return only that file as response. """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.cd(env.maintenance_mode_path):
        c.run('mv maintenance.html.off maintenance.html')

@task
def maintenanceoff(_ctx):
    """ Turn off maintenance mode by moving the maintenance.html file
        where nginx won't see it anymore. """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.cd(env.maintenance_mode_path):
        c.run('mv maintenance.html maintenance.html.off')
    
@task
def migrate(_ctx):
    """ Run a django migrate """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.prefix(f'source {env.virtualenv_path}/bin/activate'):
        c.run(f'{env.path}/manage.py migrate --fake-initial')
    
@task
def showmigrations(_ctx):
    """ Run a django showmigrations """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.prefix(f'source {env.virtualenv_path}/bin/activate'):
        c.run(f'{env.path}/manage.py showmigrations')

@task
def collectstatic(_ctx):
    """ Run a django collectstatic """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.cd(env.path):
        with c.prefix(f'source {env.virtualenv_path}/bin/activate'):
            c.run('./manage.py collectstatic --noinput')

@task
def staticown(_ctx):
    """ Chowns all media files and collected-static files. Useful only after a portal transfer/copy """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.cd(env.path):
        c.run(f'chown -R {env.username}:www-data ./static-collected')
        c.run(f'chown -R {env.username}:www-data ./media')

@task
def compileless(_ctx):
    """ Compiles all LESS files and adds the resulting CSS file to the collected-static folder """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    
    if env.skip_compile_webpack:
        # This is a workaround, as not needing to compile JS bundles anymore means no lessc is installed.
        print('Installing lessc node_modules in cosinnus-core.')
        with c.cd(f'{env.cosinnus_src_path}'):
            c.run('npm install less lessc clean-css')
            
    with c.cd(env.path):
        c.run(
            f'{env.lessc_binary} --clean-css ./static-collected/less/cosinnus.less ./static-collected/css/cosinnus.css'
        )
        c.run(
            f'{env.lessc_binary} --clean-css ./static-collected/less/cosinnus-v3-scoped.less ./static-collected/css/cosinnus-v3-scoped.css'
        )
        for less_file in env.portal_additional_less_to_compile:
            c.run(f'{env.lessc_binary} --clean-css ./static-collected/less/{less_file}.less ./static-collected/css/{less_file}.css')

@task
def compilewebpack(_ctx):
    """ Compiles the map/conferences JS clients using webpack """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    
    if env.skip_compile_webpack:
        print('Skipping webpack compile as the JS bundles now are supplied in cosinnus-core!')
        return
    
    with c.prefix(f'source {env.virtualenv_path}/bin/activate'):
        # for compilation of the JS app translations
        with c.cd(f'{env.cosinnus_src_path}'):
            c.run('npm install')
            c.run('npm run production')  # -->can also run 'npm run dev', but it stays in watch mode
        # build conference frontend
        with c.cd(f'{env.cosinnus_src_path}/cosinnus_conference/frontend/'):
            c.run('npm install')
            c.run('npm run build')


@task
def compilehtmlemails(_ctx):
    """ This generates a project-specific set of HTML email templates that overwrite the built ones
        in cosinnus-core (templates/cosinnus/html_mail).
        By adding files with the same structure as the npm email-builder inside cosinnus-core/cosinnus/html_emails/,
        you can customize the email templates for this portal only.
        It is recommended to only replace the /src/assets/scss/_extra_scss.scss and _extra_variables.scss files! """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.prefix(f'source {env.virtualenv_path}/bin/activate'):
        # ensure all directories exist
        c.run(f'mkdir -p {env.path}/html_emails_collected')
        c.run(f'mkdir -p {env.path}/wechange/templates/cosinnus/html_mail')
        # copy cosinnus-core html emails npm project
        c.run(f'cp -R {env.cosinnus_src_path}/cosinnus/html_emails/* {env.path}/html_emails_collected/')
        # copy local repo overriding files for html emails npm project, overwriting files
        result = c.run(f'cp -R {env.path}/wechange/html_emails/* {env.path}/html_emails_collected/', warn=True)
        if result.failed: 
            print('Project does not seem to specify overriding email templates/styles. Ignoring build and continuing fabfile.')
            return
        with c.cd(f'{env.path}/html_emails_collected/'):
            # build the html emails
            result = c.run('npm run build', warn=True) # -->can also run 'npm run dev', but it stays in watch mode
            # if we fail here, the npm project has probably never been set up before
            if result.failed: 
                print('Error during npm run, trying npm install in case it has not been installed yet.')
                c.run('npm install')
                c.run('npm run build') # -->can also run 'npm run dev', but it stays in watch mode
            # copy the built email templates to our local repo template folder, where they path-replace the cosinnus-core ones
            c.run('cp -R %(path)s/html_emails_collected/dist/{digest.html,notification.html,summary_group.html,summary_item.html}* %(path)s/wechange/templates/cosinnus/html_mail/' % env)

@task
def backup(_ctx):
    """ Saves a dump of the current django psql database and places it into ~/backups/ """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.cd(env.backup_path):
        c.run(f'pg_dump -Fc -U {env.db_username} {env.db_name} > {env.db_name}_backup_$(date +%%F-%%T).sql')
        c.run('ls -lt')

@task
def rebuildindex(_ctx):
    """ Runs a django elasticsearch rebuild index, deleting the current index """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    check_confirmation()
    with c.prefix(f'source {env.virtualenv_path}/bin/activate'):
        c.run(f'{env.path}/manage.py rebuild_index -v 2')

@task
def updateindex(_ctx):
    """ Runs a django elasticsearch update index, deleting the current index """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    check_confirmation()
    with c.prefix(f'source {env.virtualenv_path}/bin/activate'):
        c.run(f'{env.path}/manage.py update_index -v 2')

@task
def pipfreeze(_ctx):
    """ Run a pip freeze """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.cd(env.path):
        with c.prefix(f'source {env.virtualenv_path}/bin/activate'):
            c.run('pip freeze')

def _pull_and_update(use_poetry_update=False, fresh_install=False):
    """ 
        Does a git pull on the main project repository, then performs 
        a poetry update to update dependencies.
        (Not a task, this is a helper function called from other tasks.) 
        
        Currently, `poetry update` doesn't work on editable dependencies, 
        see issue https://github.com/python-poetry/poetry/issues/7113.
        So we can either only do:
            - a fresh install **on a non-existing venv** 
                (because the name mismatch won't even let us reinstall without 
                deleting the venv)
                Use tas `deployresetvirtualenv()` for this.
            - or a manual update from git in the editable cosinnus repo. this
                is fine als long as no dependencies in cosinnus's setup.py 
                have changed. it does however require us to know which 
                upstream branch cosinnus-core is using, as poetry creates its
                own, disconnected 'master' branch instead of a locally named
                version of the branch it checked out.
    """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.cd(env.path):
        c.run(f'git fetch')
        c.run(f'git checkout {env.pull_branch}')
        c.run(f'git pull')
        if fresh_install:
            c.run('poetry install')
        else:
            with c.prefix(f'source {env.virtualenv_path}/bin/activate'):
                if env.legacy_mode:
                    c.run(f'pip install -Ur {env.special_requirements}')
                elif use_poetry_update:
                    c.run('poetry update')
                else:
                    with c.cd(f'{env.cosinnus_src_path}'):
                        # this is neccessary because poetry doesn't configures remote.origin.fetch in the editable repos
                        c.run(f'git config --local --add remote.origin.fetch +refs/heads/*:refs/remotes/origin/*')
                        c.run(f'git fetch --all')
                        c.run(f'git stash')
                        c.run(f'git checkout -B {env.cosinnus_pull_branch} {env.cosinnus_pull_remote}/{env.cosinnus_pull_branch}')
                        c.run(f'git pull')
                        

def _pull_and_update_frontend():
    """ 
        Does a git pull on the frontend repository, then performs 
        a poetry update to update dependencies.
        (Not a task, this is a helper function called from other tasks.) 
    """
    env = get_env()
    c = CosinnusFabricConnection(host=env.host)
    with c.cd(env.frontend_path):
        c.run(f'git fetch')
        c.run(f'git checkout {env.frontend_pull_branch}')
        c.run(f'git pull')
        c.run(f'pnpm install')
        c.run(f'pnpm run build')
        # make newly built next dist files that will be served as static accessible by nginx
        c.run(f'chown {env.username}:www-data -R .next/')
