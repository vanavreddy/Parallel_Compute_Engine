#!/usr/bin/env python3
import os
import pprint
import boto3
import sys

import pcluster.lib as pc

pp = pprint.PrettyPrinter()

cf_client = boto3.client('cloudformation')

stackname = 'Test-Cluster-2'
with open('cloudstack_cluster.yaml', 'r') as cf_file:
    cft_template = cf_file.read()
    params = [{"ParameterKey": "KeyName", "ParameterValue": "controller_keypair"}, {"ParameterKey": "InstanceCount", "ParameterValue": "1"}]
    capabs = ['CAPABILITY_NAMED_IAM','CAPABILITY_AUTO_EXPAND']
    cf_client.create_stack(StackName=stackname, TemplateBody=cft_template, Parameters=params, Capabilities=capabs)

waiter = cf_client.get_waiter('stack_create_complete')

waiter.wait(
    StackName=stackname,
)

sys.exit()


'''
ec2 = boto3.resource('ec2')

# create VPC
vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
# we can assign a name to vpc, or any resource, by using tag
vpc.create_tags(Tags=[{"Key": "Name", "Value": "vpc_controller"}])
vpc.wait_until_available()
print(vpc.id)

f = open('conf.txt', 'w+')
f.write('vpc_id:'+vpc.id+'\n')

# create then attach internet gateway
ig = ec2.create_internet_gateway()
vpc.attach_internet_gateway(InternetGatewayId=ig.id)
f.write('igw_id:'+ig.id+'\n')
print(ig.id)

# create a route table and a public route
route_table = vpc.create_route_table()
route = route_table.create_route(
    DestinationCidrBlock='0.0.0.0/0',
    GatewayId=ig.id
)
print(route_table.id)

f.write('rtb_id:'+route_table.id+'\n')

# create subnet
subnet = ec2.create_subnet(CidrBlock='10.0.2.0/24', VpcId=vpc.id)
print(subnet.id)

f.write('subnet_id:'+subnet.id+'\n')

# associate the route table with the subnet
route_table.associate_with_subnet(SubnetId=subnet.id)
'''

HEAD_NODE_SUBNET = 'subnet-06c72b747bd512c00'
COMPUTE_NODE_SUBNET = 'subnet-06c72b747bd512c00'

#HEAD_NODE_SUBNET = subnet.id
#COMPUTE_NODE_SUBNET = subnet.id
KEY_NAME = 'controller_keypair'


CONFIG = {'Image': {'Os': 'ubuntu2004'},
          'HeadNode': {'InstanceType': 'hpc7g.4xlarge',
                       'Networking': {'SubnetId': HEAD_NODE_SUBNET},
                       'Ssh': {'KeyName': KEY_NAME}},
          'Scheduling': {'Scheduler': 'slurm',
                         'SlurmQueues':
                         [{'Name': 'q0',
                           'ComputeResources':
                           [{'Name': 'cr1', 'InstanceType': 'hpc7g.4xlarge',
                               'MinCount': 0, 'MaxCount': 2}],
                           'Networking': {'SubnetIds': [COMPUTE_NODE_SUBNET]}}]}}

pp.pprint(
    pc.create_cluster(
        cluster_name='mycluster-1', cluster_configuration=CONFIG))
