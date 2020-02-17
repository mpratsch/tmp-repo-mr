#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The output of the yaml file is not well formatted but it's working tho.
It reads the data via the aws-cli and copies it into a yaml file.
Then with an jinja2 template the values will be read to create a
Grafana Dashboard
"""
from sys import exit
import yaml
import boto3

role_to_assume = 'arn:aws:iam::xxxxxxxxxxxx:role/Monitoring-Create-Grafana-Dashboards'
role_session_name = 'create_grafana_dashboard'
region = 'eu-central-1'
protocol = 'https://'
domain = 'amazonaws.com'
session = boto3.session.Session()
liste = dict()

#-------------------- Functions ---------------------------------
def get_credentials():
    """Fetch tmp credentials"""
    try:
        sts = session.client('sts')
        response = sts.assume_role(
            RoleArn=role_to_assume,
            RoleSessionName=role_session_name
        )
        creds = response['Credentials']
    except Exception as e:
        print("Exception: %s" % str(e))
        exit()
    return creds

########################################
# VPC / VPN
########################################
def get_vpn_connection_details(creds):
    """Fetch the vpn id and name from AWS tags"""
    vpns = list()
    try:
        ec2 = boto3.client('ec2',
                           aws_access_key_id=creds['AccessKeyId'],
                           aws_secret_access_key=creds['SecretAccessKey'],
                           aws_session_token=creds['SessionToken'],
                           endpoint_url=f'{protocol}ec2.{region}.{domain}',
                           region_name=region
                           )
        resp = ec2.describe_vpn_connections()
    except Exception as e:
        print("Exception: %s" % str(e))
        exit()
    finally:
        for vpn in resp['VpnConnections']:
            dictory = dict()
            dictory['id'] = vpn['VpnConnectionId']
            for tag in vpn['Tags']:
                if tag['Key'] == 'Name':
                    dictory['name'] = tag['Value']
                else:
                    dictory['name'] = vpn['VpnConnectionId']
            vpns.append(dictory)
    return vpns

#-------------------- Main ---------------------------------
creds = get_credentials()

liste['vpnconnections'] = get_vpn_connection_details(creds)

with open('roles/datadog/vars/vpn-config.yaml', 'w') as f:
    f.write(yaml.dump(liste, default_flow_style=False))
