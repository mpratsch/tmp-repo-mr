#!/usr/bin/env python
# -*- coding: UTF-8 -*-
""" 
Author: Martina Rath
Email: mpratscher@gmail.com
Date: 2020-02-20

This Lambda function checks non-compliant resources of mandatory tags.
The format is a simple HTML for now and the result will be be pushed
to an S3 bucket.
The input of this comes from a config rule where it's easy to find out
the NON_COMPLIANT resources.
"""

import os
from botocore.exceptions import ClientError
import boto3

COMPLIANCE_TAGS = ['Contact','CostCenter','Environment','Compliance']
s3bucket_name = os.environ['BUCKET_NAME']
config_rule_name = os.enviro['CONFIG_RULE_NAME']
output_path = '/tmp/output.html'
missing_tag = {}

f = open(output_path, 'w')

def push_to_s3():
    """Pushes the generated file to the S3 bucket"""
    # Create an S3 client
    s3 = boto3.client('s3')
    with open(output_path) as file:
        object = file.read()
    
    response = s3.put_object(
        ServerSideEncryption='AES256',
        Bucket=s3bucket_name,
        Key='output.html',
        Body=object
        #ACL='public-read'
    )
    return response

def get_resource_tags(instance):
    """ Loops trough all resources to get the tags"""
    f.write(f'<p>{instance}</p>')
    remain = COMPLIANCE_TAGS.copy()
    tags_list = list()
    resource_name = ''
    contact_name = ''
    try:
        client = boto3.client('ec2')
        resp = client.describe_tags(
            Filters=[
                {
                    'Name': 'resource-id',
                    'Values': [f'{instance}']
                }
            ]
        )
        for tag in resp['Tags']:
            if tag['Key'] in COMPLIANCE_TAGS:
                remain.remove(tag['Key'])
            if 'Name' in tag['Key']:
                resource_name = tag['Value']
            if 'Contact' in tag['Key']:
                contact_name = tag['Value']
        
        if resource_name:
            f.write(f'<p><strong>Name: {resource_name}</strong></p>')
        if contact_name:
            f.write(f'<p><strong>Contact: {contact_name}</strong></p>')

        if remain:
            missing_tag[instance] = remain
            f.write(f'<strong style="color:red;>NOT COMPLIANT!</strong> Missing tags:')
            f.write('<ul>')
            for missing in remain:
                f.write(f'<li>{missing}</li>')
            f.write('</ul><hr>')
        else:
            f.write(f'{instance} is COMPLIANT!')
        tags_list = list()
    except ClientError as errormsg:
        print(f'error: {errormsg}')

def get_compliant_per_rule(name):
    """Gets a list of all non compliant rules"""
    try:
        client = boto3.client('config')
        paginator = client.get_paginator('get_compliance_details_by_config_rule')
        resp = paginator.paginate(
            ConfigRuleName=name,
            ComplianceTypes=['NON_COMPLIANT','NOT_APPLICABLE']
        )
    except ClientError as errormsg:
        print(f'error: {errormsg}')
    check_resource_type = ''
    for pag in resp:
        for eventresults in pag['EvaluationResults']:
            for event1 in eventresults['EvaluationResultIdentifier']: #['EvaluationResultQualifier']:
                if 'EvaluationResultQualifier' in event1:
                    resourcetype = eventresults['EvaluationResultIdentifier'][event1]['ResourceType'].replace('AWS::','').replace('::','/')
                    resourceid = eventresults['EvaluationResultIdentifier'][event1]['ResourceId']
                    if check_resource_type != resourcetype:
                        f.write(f'<h1>{resourcetype}</h1>')
                    get_resource_tags(resourceid)
                    check_resource_type = resourcetype

def lambda_handler(event, context):
    f.write('<html><head></head><body>')
    get_compliant_per_rule(config_rule_name)
    f.write('</body></html>')
    response = push_to_s3()
    return {
        'body': response
        
    }

