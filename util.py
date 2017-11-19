import requests
import time
from operator import attrgetter
from requests.exceptions import HTTPError, Timeout, ConnectionError
from bravado.client import SwaggerClient
from bravado.exception import HTTPServerError, HTTPNotFound, HTTPForbidden, HTTPError
from xml.etree import cElementTree as ET
from pprint import PrettyPrinter

from config import *

pprinter = PrettyPrinter()

for retry in range(5):
    try:
        esi_client = SwaggerClient.from_url("https://esi.tech.ccp.is/latest/swagger.json?datasource=tranquility")
        xml_client = requests.Session()
        break
    except (HTTPServerError, HTTPNotFound), e:
        if retry < 4:
            print('Attempt #{} - {}'.format(retry, e))
            time.sleep(60)
            continue
        raise

def name_to_id(name, name_type):
    name_id = esi_api('Search.get_search',
                        categories=[name_type],
                        search=name,
                        strict=True).get(name_type)[0]
    return name_id

def get_access_token(refresh, client_id, client_secret):
    """
    Grab API access token using refresh token
    """
    params = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh
    }
    for retry in range(5):
        try:
            token_response = requests.post('https://login.eveonline.com/oauth/token', data=params, auth=(client_id, client_secret))
            token_response.raise_for_status()
        except (HTTPError, Timeout, ConnectionError), e:
            if retry < 4:
                print ('Attempt #{} - {}'.format(retry, e))
                time.sleep(60)
                continue
            raise
    return token_response.json()['access_token']

access_token = get_access_token(SSO_REFRESH_TOKEN, SSO_APP_ID, SSO_APP_KEY)
xml_client.params = {
    'accessToken': access_token,
    'accessType': 'corporation'
}


def annotate_element(row, dict):
    """Sets attributes on an Element from a dict"""
    for key, value in dict.iteritems():
        row.set(key, str(value))


def esi_api(endpoint, **kwargs):
    esi_func_finder = attrgetter(endpoint)
    esi_func = esi_func_finder(esi_client)
    result = {}
    for retry in range(5):
        try:
            result = esi_func(**kwargs).result()
            return result
        except (HTTPServerError, HTTPNotFound), e:
            if retry < 4:
                print('{} ({}) attempt #{} - {}'.format(endpoint, kwargs, retry+1, e))
                time.sleep(60)
                continue
            e.message = e.swagger_result
            raise
        except HTTPForbidden, e:
            e.message = e.swagger_result.error
            raise

def xml_api(endpoint, xpath=None, params=None):
    """
    Accesses CCP XML api in a useful way and returns ET root
    """
    xml_root = None
    for retry in range(5):
        try:
            xml_response = xml_client.get('https://api.eveonline.com' + endpoint, params=params)
            xml_root = ET.fromstring(xml_response.content)
            xml_response.raise_for_status()
            if xpath:
                xml = xml_root.findall(xpath)
            else:
                xml = xml_root
            return xml
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError), e:
            if xml_root:
                xml_error = xml_root.find('.//error')
                message = "Error code {}: {}".format(xml_error.get('code'), xml_error.text)
            else:
                message = "Error: {}".format(e)
            if retry < 4:
                print('{} ({}) attempt #{} - {}'.format(endpoint, params, retry+1, message))
                time.sleep(60*retry)
                continue
            e.args = (message,)
            raise


def notify_slack(messages):
    params = {
        'text': '\n\n'.join(messages)
    }
    if SLACK_CHANNEL:
        params['channel'] = SLACK_CHANNEL
    results = requests.post(OUTBOUND_WEBHOOK, json=params)
    results.raise_for_status()
    print params