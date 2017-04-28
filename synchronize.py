#!/usr/bin/python
# coding: utf-8

import os
import sys
import xmlrpclib
import requests
import subprocess
import logging
import ConfigParser


logger = logging.getLogger('syncronize.py')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s - %(message)s]')
ch.setFormatter(formatter)
logger.addHandler(ch)


class Rpc(object):

    def __init__(self):
        self.url = '%s/xmlrpc/' % os.environ.get('ODOO_URL', 'http://nappa.vauxoo.com:2406')
        self.db = os.environ.get('ODOO_DB', 'openerp_test')
        self.username = os.environ.get('ODOO_USERNAME', 'admin')
        self.password = os.environ.get('ODOO_USERNAME', 'admin')

    def login(self):
        self._user = xmlrpclib.ServerProxy(self.url + 'common').login(
            self.db, self.username, self.password)
        if not self._user:
            raise Exception('Not login into %s' % self.url)

    def execute(self, *args, **kargs):
        return xmlrpclib.ServerProxy(self.url + 'object').execute(
            self.db, self._user, self.password, *args, **kargs)


class WeblateAPI(object):

    def _init_api(self, url, token):
        self._url = url
        self._token = token
        self._session = requests.Session()
        self._session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'syn_runbot_weblate',
            'Authorization': 'Token %s' % self._token
        })
        self._api_projects = self._session.get(self._url + '/projects/').json()['results']

    def create_project(self, repo, slug):
        slug = slug.replace('/', '-')
        if (not any([pre for pre in ['http://', 'https://'] if pre in repo])
                and '@' in repo):
            repo = 'http://' + repo.split('@')[1:].pop().replace(':', '/')
        cmd = []
        cmd.extend(['django-admin', 'shell', '-c',
                    'import weblate.trans.models.project as project;'
                    'project.Project(name=\'{0}\', slug=\'{0}\', web=\'{1}\').save()'.format(slug, repo)])
        logger.debug('Create project "%s"' % slug)
        logger.debug(' '.join(cmd))
        print subprocess.check_output(cmd)
        return self._session.get(self._url + '/projects/%s/' % slug).json()

    def find_or_create_project(self, project):
        repo = project['repo']
        slug = ''
        if '@' in repo:
            slug = repo.split(':')[1:].pop()
        if any([pre for pre in ['http://', 'https://'] if pre in repo]):
            slug = repo.split('/')[3:]
            slug = '/'.join(slug)
        slug = slug.replace('.git', '')
        for pro in self._api_projects:
            if slug in pro['web']:
                return pro
        return self.create_project(repo, slug)

    def create_component(self, project, branch):
        cmd = []
        cmd.extend(['django-admin',
                    'import_project', project['slug'], project['web'],
                    branch['branch_name'], '**/i18n/*.po'])
        logger.debug('Create component "%s:%s"' % (project['slug'], branch['branch_name']))
        logger.debug(' '.join(cmd))
        print subprocess.check_output(cmd)

    def import_from_runbot(self, project, branches):
        self._init_api(project['weblate_url'], project['weblate_token'])
        project = self.find_or_create_project({
            'repo': project['name']
        })
        for branch in branches:
            logger.debug('Processing branch "%s:%s"' % (project['name'], branch['branch_name']))
            self.create_component(project, branch)

    def _request_api(self, url):
        return self._session.get(self._url + url).json()


class SynRunbotWeblate(object):

    def __init__(self):
        self._rpc = Rpc()
        self._wlapi = WeblateAPI()

    def sync(self):
        self._rpc.login()
        ids = self._rpc.execute('runbot.repo', 'search',
            [['weblate_token', '!=', ''], ['weblate_url', '!=', '']])
        repos = self._rpc.execute('runbot.repo', 'read', ids)
        for repo in repos:
            logger.debug('Processing "%s" repository' % repo['name'])
            ids = self._rpc.execute('runbot.branch', 'search',
                [['uses_weblate', '=', True], ['repo_id', '=', repo['id']]])
            branches = self._rpc.execute('runbot.branch', 'read', ids)
            self._wlapi.import_from_runbot(repo, branches)
        return 0


if __name__ == '__main__':
    exit(SynRunbotWeblate().sync())
