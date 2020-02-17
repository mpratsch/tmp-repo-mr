#!/usr/bin/env python
"""
Author: Martina Rath
Date: 2020-01-24

That script is a helper to set up permissions via the Datadog API
since DD has no user management gui at the moment.
See more details
  * https://docs.datadoghq.com/account_management/rbac/role_api/?tab=example
  * https://docs.datadoghq.com/account_management/rbac/role_api/?tab=response#add-user-to-role
"""
from io import BytesIO
from sys import exit
import json
import click
from colorama import Fore
import pycurl

COLOR = {
    'cyan': Fore.CYAN,
    'reset': Fore.RESET
}
API_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
APPLICATION_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
UUID_LIST = {
    'admin':                        'f1624684-d87d-11e8-acac-efb4dbffab1c',         # Read and write permission to all of datadog
    'standard':                     'f1666372-d87d-11e8-acac-6be484ba794a',         # Read and write permission to most of datadog
    'logs_read_index_data':         '4fbb1652-dd15-11e8-9308-77be61fbb2c7',         # Read a subset of all log indexes
    'logs_modify_indexes':          '4fbd1e66-dd15-11e8-9308-53cb90e4ef1c',         # Update the definition of log indexes
    'logs_live_tail':               '4fbeec96-dd15-11e8-9308-d3aac44f93e5',         # Access the live tail feature
    'logs_write_exclusion_filters': '4fc2807c-dd15-11e8-9308-d3bfffb7f039',         # Update a subset of the exclusion filters
    'logs_write_pipelines':         '4fc43656-dd15-11e8-9308-f3e2bb5e31b4',         # Update a subset of the log pipelines
    'logs_write_processors':        '505f4538-dd15-11e8-9308-47a4732f715f',         # Update the log processors in an index
    'logs_write_archives':          '505fd138-dd15-11e8-9308-afd2db62791e',         # Update the external archives configuration
    'logs_public_config_api':       'bd837a80-6cb2-11e9-8fc4-339b4b012214',         # Access the Logs Public Config API (r/w)
    'logs_generate_metrics':        '06f715e2-aed9-11e9-aac6-eb5723c0dffc',         # Access the Generate Metrics feature
    'dashboards_read':              '2147a4f0-d3d9-11e9-a614-83d5d3c791ee',         # Ability to view dashboards
    'dashboards_write':             '2149e512-d3d9-11e9-a614-bb8f0dcf0205',         # Ability to create and change dashboards
    'dashboards_public_share':      '214c10b2-d3d9-11e9-a614-3759c7ad528f',         # Ability to share dashboards externally
    'monitors_read':                'c898551e-d8b2-11e9-a336-e3a79c23bd8d',         # Ability to view monitors
    'monitors_write':               'cdc3e3d2-d8b2-11e9-943b-e70db6c573b8',         # Ability to change, mute, and delete monitors
    'monitors_downtime':            'd3159858-d8b2-11e9-a336-e363d6ef331b'          # Ability to set downtimes for your monitors
}
# Reverse the mapping for reverse lookup
UUID_LIST_REVERSE = dict()
UUID_LIST_REVERSE = dict(map(reversed, UUID_LIST.items()))
DATA = {}
URL = ''
DATADOG_API_URL = 'https://app.datadoghq.eu/api/'
APIVERSION = 'v2'
HEADERS = [
    'Content-Type:application/json',
    'DD-API-KEY:' + API_KEY,
    'DD-APPLICATION_KEY:' + APPLICATION_KEY
]
BUFFER = BytesIO()

@click.group('roles')
def roles():
    """Datadog Permission Management"""
    pass

@roles.command('list-permissions')
def list_all_permissions():
    """Lists all permissions (Name and UUID)"""
    for key, value in UUID_LIST.items():
        print(f'{key}\t{value}')


@roles.command('get-user-permission-set')
@click.argument('useruuid')
def get_user_permission_set(useruuid):
    """Lists all permissions of a user"""
    c = start_handler()
    URL = f'{APIVERSION}/users/{useruuid}/permissions'
    c.setopt(c.WRITEDATA, BUFFER)
    perform_request(c, URL)
    body = json.loads(BUFFER.getvalue())
    for output in body['data']:
        for key, value in output.items():
            if 'attributes' in key:
                print(f'{value["name"]}\t{value["group_name"]}\t{value["display_name"]}')

@roles.command('get-users-of-roles')
@click.argument('rolename')
def get_users_of_roles(rolename):
    """Lists all users of a role - [rolename]."""
    role_uuid = get_all_permissions(rolename)
    user_uuid = None
    c = start_handler()
    URL = f'{APIVERSION}/roles/{role_uuid}/users'
    c.setopt(c.WRITEDATA, BUFFER)
    perform_request(c, URL)
    body = json.loads(BUFFER.getvalue())
    for output in body['data']:
        for key, value in output.items():
            if 'attributes' in key:
                if rolename in body['included'][0]['attributes']['name']:
                    user_uuid = output['id']
                    print(value['email'], end=' | ')
                    print(user_uuid)
    return user_uuid

@roles.command('list-monitor-downtimes')
def list_all_monitor_downtimes():
    """Lists all monitor downtime configurations"""
    c = start_handler()
    URL = f'v1/downtime'
    c.setopt(c.WRITEDATA, BUFFER)
    perform_request(c, URL)
    body = json.loads(BUFFER.getvalue())
    print(body)

def get_all_permissions(rolename=None):
    """Lists all roles and their permissions - [rolename]."""
    URL = f'{APIVERSION}/roles'
    user_uuid = None
    c = start_handler()
    c.setopt(c.WRITEDATA, BUFFER)
    perform_request(c, URL)
    body = json.loads(BUFFER.getvalue())
    for output in body['data']:
        for key, value in output.items():
            if 'attributes' in key:
                if rolename:
                    if rolename in value['name']:
                        user_uuid = output['id']
                        break
                else:
                    print(COLOR['cyan'] + '#############################################')
                    print(value['name'], end=' |')
                    print(' (%s)' % output['id'])
                    print('---------------------------------------------')
                    print(COLOR['reset'] + '', end='')
                    for permission in output['relationships']['permissions']['data']:
                        print(f'{UUID_LIST_REVERSE[permission["id"]]} (permission["id"])')
    return user_uuid

@roles.command('list-roles')
def list_all_roles():
    """Lists all roles"""
    URL = f'{APIVERSION}/roles'
    c = start_handler()
    c.setopt(c.WRITEDATA, BUFFER)
    perform_request(c, URL)
    body = json.loads(BUFFER.getvalue())
    for output in body['data']:
        for attribute in output['attributes']:
            if 'name' in attribute:
                print(f'{output["attributes"][attribute]}\t| {output["id"]}')

@roles.command('list-all-permissions')
def get_permissions_of_role():
    """Lists all roles and their permissioins."""
    get_all_permissions()

@roles.command('get-permission-of-role')
@click.argument('rolename')
def get_permissions_of_role(rolename):
    """Lists the permission of a role - [rolename]."""
    role_uuid = get_all_permissions(rolename)
    URL = f'{APIVERSION}/roles/{role_uuid}/permissions'
    c = start_handler()
    c.setopt(c.WRITEDATA, BUFFER)
    perform_request(c, URL)
    body = json.loads(BUFFER.getvalue())
    for output in body['data']:
        for key, value in output.items():
            if 'attributes' in key:
                print(value['name'])

@roles.command('role-create')
@click.argument('rolename')
def create_role(rolename):
    """Creates a new role"""
    c = start_handler()
    URL = f'{APIVERSION}/roles'
    DATA = {'data': {'type': 'roles', 'attributes': {'name': rolename}}}
    PF = json.dumps(DATA)
    c.setopt(c.POSTFIELDS, PF)
    perform_request(c, URL)

@roles.command('role-delete')
@click.argument('role_uuid')
def create_role(role_uuid):
    """Deletes a role"""
    c = start_handler()
    URL = f'{APIVERSION}/roles/{role_uuid}'
    c.setopt(pycurl.CUSTOMREQUEST, "DELETE")
    perform_request(c, URL)

@roles.command('list-users')
def list_all_users():
    """Lists all users"""
    c = start_handler()
    URL = f'{APIVERSION}/users'
    c.setopt(c.WRITEDATA, BUFFER)
    perform_request(c, URL)
    body = json.loads(BUFFER.getvalue())
    for output in body['data']:
        for key, value in output.items():
            if 'attributes' in key:
                print(value['email'], end=' | ')
                print(f'{value["name"]}\n\t{output["id"]}')

@roles.command('add-user-to-role')
@click.argument('roleuuid')
@click.argument('useruuid')
def add_user_to_role(roleuuid, useruuid):
    """Adds a user to a role - [roleuuid,useruuid]."""
    c = start_handler()
    URL = f'{APIVERSION}/roles/{roleuuid}/users'
    DATA = {'data': {'type': 'users', 'id': useruuid}}
    PF = json.dumps(DATA)
    c.setopt(c.POSTFIELDS, PF)
    perform_request(c, URL)

@roles.command('grant_permisson')
@click.argument('roleuuid')
@click.argument('permissionid')
def grant_permission(roleuuid, permissionid):
    """Grants a permission to a role"""
    c = start_handler()
    URL = f'{APIVERSION}/roles/{roleuuid}/permissions'
    DATA = {'data': {'type': 'permissions', 'id': permissionid}}
    PF = json.dumps(DATA)
    c.setopt(c.POSTFIELDS, PF)
    perform_request(c, URL)

@roles.command('revoke_permisson')
@click.argument('roleuuid')
@click.argument('permissionid')
def grant_permission(roleuuid, permissionid):
    """Revoke permission to a role"""
    c = start_handler()
    URL = f'{APIVERSION}/roles/{roleuuid}/permissions'
    DATA = {'data': {'type': 'permissions', 'id': permissionid}}
    PF = json.dumps(DATA)
    c.setopt(c.POSTFIELDS, PF)
    c.setopt(pycurl.CUSTOMREQUEST, "DELETE")
    perform_request(c, URL)

def start_handler():
    """Starts the pycurl handler"""
    c = pycurl.Curl()
    c.setopt(c.VERBOSE, False)
    c.setopt(c.HTTPHEADER, HEADERS)
    return c

def perform_request(c, URL):
    """Performs the pycurl request"""
    BUFFER.truncate(0)
    BUFFER.seek(0)
    c.setopt(c.URL, DATADOG_API_URL + URL)
    try:
        print(f'Connection to URL: {DATADOG_API_URL}{URL}')
        c.perform()
        print(f'{c.getinfo(c.RESPONSE_CODE)}')
        if c.getinfo(c.RESPONSE_CODE) is not 200:
            print(f'Check the output!')
            exit()
    finally:
        c.close()

if __name__ == "__main__":
    roles()
    #get_all_permissions()
