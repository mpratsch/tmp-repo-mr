#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#####################################################################
# Do not touch manually, this will be overridden by Ansible anyways! #
#####################################################################
The script gathers the state of the DX/Virtual Interfaces and the
Transit Gateway Attachments, used by Prometheus, since there is no
metric in CloudWatch available.
"""
from sys import exit
import time
import boto3
from botocore.exceptions import ClientError
from prometheus_client import start_http_server #, Summary, CollectorRegistry, Gauge, push_to_gateway, Counter
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY

role_to_assume = 'arn:aws:iam::xxxxxxxxxxxx:role/Monitoring-Create-Grafana-Dashboards'
role_session_name = 'create_grafana_dashboard'
region = 'eu-central-1'

session = boto3.session.Session()
instancelabel = "custom-aws-exporter"

class CustomCollector(object):
    """Class to collects all metrics"""
    def collect(self):
        def get_credentials():
            """Get the creds of the the session"""
            try:
                sts = session.client('sts')
                response = sts.assume_role(
                    RoleArn=role_to_assume,
                    RoleSessionName=role_session_name
                )
                creds = response['Credentials']
            except ClientError as e:
                print("Exception: %s" % str(e))
                exit()
            return creds

        creds = get_credentials()

        #######################################
        # VPC /Transit Gateway Attachments
        #######################################
        g = GaugeMetricFamily(
            'aws_transitgateway_attachment_state',
            'Status of Transit Gateway Attachments (describe-transit-gateway-attachments)',
            labels=['instance', 'tgw_rtb_name', 'tgw_attach_id', 'tgw_attachment_state', 'resourceowner_id',
                    'resourcetype', 'status']
            )
        try:
            ec2 = session.client('ec2',
                                 aws_access_key_id=creds['AccessKeyId'],
                                 aws_secret_access_key=creds['SecretAccessKey'],
                                 aws_session_token=creds['SessionToken'],
                                 region_name=region)
            resp = ec2.describe_transit_gateway_attachments()
            for output in resp['TransitGatewayAttachments']:
                if output['State'] == 'available':
                    status = '1.0'
                else:
                    if output['State'] == 'deleted':
                        pass
                    else:
                        status = '0.0'
                if output['Tags']:
                    tgw_attachment_name = output['Tags'][0]['Value']
                else:
                    tgw_attachment_name = output['TransitGatewayAttachmentId']
                labels = {
                    'instance': instancelabel,
                    'tgw_rtb_name': tgw_attachment_name,
                    'tgw_attach_id': output['TransitGatewayAttachmentId'],
                    'tgw_attachment_state': output['State'],
                    'resourceowner_id': output['ResourceOwnerId'],
                    'resourcetype': output['ResourceType'],
                }
                g.add_metric(labels.values(), status)
        except Exception as e:
            print('describe-transit-gateway-attachments failed: %s' % str(e))
        finally:
            yield g

        #######################################
        # Direct Connect / Virtual Interfaces
        #######################################
        a = GaugeMetricFamily(
            'aws_directconnect_virtualinterface_state',
            'Status of Direct Connect Virtual Interfaces (describe_virtual_interfaces)',
            labels=['instance', 'vif_id', 'vif_type', 'vif_name', 'vlan',
                    'vif_state', 'dx_id', 'status']
        )
        try:
            dx = session.client('directconnect',
                                aws_access_key_id=creds['AccessKeyId'],
                                aws_secret_access_key=creds['SecretAccessKey'],
                                aws_session_token=creds['SessionToken'],
                                region_name=region)
            resp = dx.describe_virtual_interfaces()
            for output in resp['virtualInterfaces']:
                if output['virtualInterfaceState'] == 'available':
                    status = '1'
                else:
                    status = '0'
                labels = {
                    'instance': instancelabel,
                    'vif_id': output['virtualInterfaceId'],
                    'vif_type': output['virtualInterfaceType'],
                    'vif_name': output['virtualInterfaceName'],
                    'vlan': str(output['vlan']),
                    'vif_state': output['virtualInterfaceState'],
                    'dx_state': output['directConnectGatewayId']
                }
                a.add_metric(labels.values(), status)
        except ClientError as e:
            print('describe_virtual_interfaces failed: %s' % str(e))
        finally:
            yield a

if __name__ == '__main__':
    print("Starting http server on port 8000")
    start_http_server(8000)
    REGISTRY.register(CustomCollector())
    while True:
        time.sleep(1)
