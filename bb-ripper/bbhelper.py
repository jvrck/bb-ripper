import requests
import os
import json
import logging

BB_API_ENDPOINT='https://api.bitbucket.org/2.0'

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(level=LOGLEVEL)

class BBProject:
    """
    Bitbucket Projects 
    Contains the structure of a bitbucket project
    Takes json response object in constructor
    """
    def __init__(self, json):
        self.name = json['name']
        self.key = json['key']
        self.repo_rest_url = json['links']['repositories']['href']

    @staticmethod
    def GetProjects(workspace_name):
        """
        Static method to get all projects for a workspace
        """
        request_endpoint = "{0}/workspaces/{1}/projects".format(BB_API_ENDPOINT, workspace_name)
        logging.info("Get projects request endpoint %s", request_endpoint)

        session = requests.session()
        session.auth = (os.environ['BB_USER'], os.environ['BB_PASSWORD'])

        projects_request = session.get(request_endpoint)
        projects_json = json.loads(projects_request.text)
        projects = []
        
        for p in projects_json['values']:
            projects.append(BBProject(p))

        session.close()
        return projects


class BBRepo:
    """
    Bitbucket Repo
    Contains the structure of a bitbucket repo
    Takes json response object in constructor
    """
    def __init__(self, data):
        self.name = data['name']
        self.project = data['project']
        self.links = data['links']['clone']

        for l in self.links:
            if l['name'] == 'ssh':
                self.ssh = l['href']
            if l['name'] == 'https':
                self.https = l['href']

    @staticmethod
    def GetWorkspaceRepos(workspace_name):
        request_endpoint = "{0}/repositories/{1}".format(BB_API_ENDPOINT, workspace_name)
        logging.info("Get workspace repos request endpoint %s", request_endpoint)

        session = requests.session()
        session.auth = (os.environ['BB_USER'], os.environ['BB_PASSWORD'])

        repos = []
    
        process = True        
        while process:
            repos_request = session.get(request_endpoint)
            repos_json = json.loads(repos_request.text)
            for r in repos_json['values']:
                repos.append(BBRepo(r))

            logging.info("Repos returned count ... %s", request_endpoint)

            if 'next' in repos_json:
                request_endpoint = repos_json['next']
            else:
                process = False
                
        session.close()
        return repos
