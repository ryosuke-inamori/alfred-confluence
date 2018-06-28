import argparse
import json
import sys
from HTMLParser import HTMLParser
from lib.workflow import Workflow, ICON_INFO, web, PasswordNotFound
from os.path import expanduser
from urlparse import urlparse

log = None

PROP_BASEURL = 'confluence_baseUrl'
PROP_USERNAME = 'confluence_username'
PROP_PASSWORD = 'confluence_password'

VERSION = '1.0.2'


def getConfluenceBaseUrl():
    if wf.settings.get(PROP_BASEURL):
        return wf.settings[PROP_BASEURL]
    else:
        wf.add_item(title='No Confluence Base URL set.',
            subtitle='Type confluence_baseurl <baseUrl> and hit enter.',
            valid=False
            )
        wf.send_feedback()
        return 0


def getConfluenceUsername():
    if wf.settings.get(PROP_USERNAME):
        return wf.settings[PROP_USERNAME]
    else:
        wf.add_item(
            title='No Confluence Username set. Please run confluence_username',
            subtitle='Type confluence_username <username> and hit enter.',
            valid=False
            )
        wf.send_feedback()
        return 0


def getConfluencePassword():
    try:
        return wf.get_password(PROP_PASSWORD)
    except PasswordNotFound:
        wf.add_item(
            title='No Confluence Password set. Please run confluence_password',
            subtitle='Type confluence_password <password> and hit enter.',
            valid=False
            )
        wf.send_feedback()
        return 0


def main(wf):
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseUrl', dest='baseUrl', nargs='?', default=None)
    parser.add_argument('--username', dest='username', nargs='?', default=None)
    parser.add_argument('--password', dest='password', nargs='?', default=None)
    parser.add_argument('query', nargs='?', default=None)
    args = parser.parse_args(wf.args)


    if args.baseUrl:
        wf.settings[PROP_BASEURL] = args.baseUrl
        return 0

    if args.username:
        wf.settings[PROP_USERNAME] = args.username
        return 0

    if args.password:
        wf.save_password(PROP_PASSWORD, args.password)
        return 0

    try:
        # lookup config for system
        args = wf.args[0].split()
        config = findConfig(args)

        if config.get('isFallback') is None:
            query = ' '.join(args[1:])
        else:
            query = ' '.join(args)

    except:
        query = wf.args[0]
        config = dict(
            baseUrl=getConfluenceBaseUrl(),
            prefix='',
            username=getConfluenceUsername(),
            password=getConfluencePassword()
            )

    # query Confluence
    url = config['baseUrl'] + "/rest/api/search"

    log.debug('Quick Search URL: ' + url)

    if config['type'] == 'title':
        r = web.get(url, params=dict(cql="space="+config['space']+" and type=page and title~\"*"+query+"*\" order by lastModified desc"), headers=dict(Accept='application/json', authorization="Basic " + (config['username'] + ":" + config['password']).encode("base64")[:-1]))
    else:
        r = web.get(url, params=dict(cql="space="+config['space']+" and type=page and siteSearch~\""+query+"\" order by lastModified desc"), headers=dict(Accept='application/json', authorization="Basic " + (config['username'] + ":" + config['password']).encode("base64")[:-1]))

    # throw an error if request failed
    # Workflow will catch this and show it to the user
    r.raise_for_status()

    # Parse the JSON returned by pinboard and extract the posts
    result = r.json()
    contentGroups = result['results']

    # Loop through the returned posts and add an item for each to
    # the list of results for Alfred

    for content in contentGroups:
        wf.add_item(title=htmlParser.unescape(content['title']),
            arg=getBaseUrlWithoutPath(config['baseUrl']) + "/wiki"+ content['url'],
            subtitle=htmlParser.unescape(content['excerpt']),
            valid=True,
            icon='assets/content-type-page.png')

    # Send the results to Alfred as XML
    wf.send_feedback()


def findConfig(args):
    homeDir = expanduser('~')
    with open(homeDir + '/.alfred-confluence.json') as configFile:
        configs = json.load(configFile)


    if len(args) > 1:
        for config in configs:
            if args[0].lower() == config['key'].lower():
                return config

    # Fallback to first entry
    configs[0]['isFallback'] = True
    return configs[0]


def getBaseUrlWithoutPath(baseUrl):
    parsedBaseUrl = urlparse(baseUrl)
    baseUrlWithoutPath = parsedBaseUrl.scheme + '://' + parsedBaseUrl.hostname
    return baseUrlWithoutPath


if __name__ == u'__main__':
    wf = Workflow(update_settings={
        'github_slug': 'skleinei/alfred-confluence',
        'version': VERSION
        })
    htmlParser = HTMLParser()
    log = wf.logger

    if wf.update_available:
        # Add a notification to top of Script Filter results
        wf.add_item('New version of the Alfred Confluence workflow available',
                    'Hit enter twice to to install the update.',
                    autocomplete='workflow:update',
                    icon=ICON_INFO)

    sys.exit(wf.run(main))
