"""
Fabric command script for project asklet_site.

For most production deployments, you'll want to do:

    fab prod deploy2

For quick deployments without any media changes, just do:

    fab prod deploy3

Download a snapshot of the production database:

    time fab prod db.dump:to_local=1
    
Load a database snapshot to the local dev database:

    time fab dev db.load:"/tmp/asklet_site_$(date +%Y%m%d).sql.gz"

Or download and load it all in one command:

    time fab prod db.dump:to_local=1 dev db.load:"/tmp/asklet_site_$(date +%Y%m%d).sql.gz"
    
"""
import os
import sys
import re

from fabric.api import task, env, local, run, sudo

import burlap

set_site = common.set_site

if not env.SITE:
    set_site('asklet_site')

@task
def collect_static():
    """
    Runs Django's collectstatic command.
    """
    local('cd src; ./manage collectstatic --noinput')

@task
def push_static():
    """
    Collects and uploads all our static media.
    """
    collect_static()
#    if env.s3_sync_enabled:
#        s3.sync(sync_set='static', auto_invalidate=True)
    apache.sync_media(sync_set='static')

@task
def get_conceptnet_data(dryrun=0):
    dryrun = int(dryrun)
    from burlap.dj import render_remote_paths
    render_remote_paths()
    cn_path = os.path.join(env.remote_app_dir, '.env/lib/python2.7/site-packages/conceptnet5/support_data')
    
    cmd = 'mkdir -p %s' % cn_path
    print cmd
    if not dryrun:
        run(cmd)
        
    cmd = 'wget -P %s https://raw.githubusercontent.com/commonsense/conceptnet5/master/conceptnet5/support_data/iso639.txt' % cn_path
    print cmd
    if not dryrun:
        run(cmd)

@task
def deploy1():
    """
    Runs all deployment tasks against the target.
    
    This could take a while and should only be done for fresh installs.
    """
    
    # Configure user.
    user.togroups()
    
    # Install system packages.
    package.install_required(type='system')
    package.install()
    
    # Cache and install Python packages.
    pip.update()
    pip.install()
    
    # Upload static media.
    #push_static()
    
    # Cache and deploy our application code.
    tarball.create()
    tarball.deploy()
    
    # Configure and restart all other services.
    #service.configure()#this wipes out all other sites
    service.deploy()
    service.restart()

@task
def deploy2():
    """
    Uploads our application code, static media, and restarts Apache.
    Assumes deploy_full() has been run at least once before.
    """
    push_static()
    deploy3(dodb=1)

@task
def deploy3(dodb=0):
    """
    Simply uploads our application code and restarts Apache.
    Assumes deploy_full() has been run at least once before.
    """
    tarball.create()
    tarball.deploy()
    if int(dodb):
        #db.migrate()
        db.update()
    apache.reload()
    #service.restart()
    