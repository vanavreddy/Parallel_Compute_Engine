import boto3
import time
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

aws_resources = {}
saved_cofig_file = './saved_config.txt'
f = open(saved_cofig_file, 'r')

lines = f.readlines()
for line in lines:
    line = line.strip()
    aws_resources[line.split(':')[0]] = line.split(':')[1]
f.close()

print(aws_resources)

ec2 = boto3.client('ec2')
ec2.start_instances(InstanceIds=[aws_resources['instance_id']])
time.sleep(60)
ec2.terminate_instances(InstanceIds=[aws_resources['instance_id']])
time.sleep(60)
ec2.delete_security_group(GroupId=aws_resources['sec_group_id'])
time.sleep(5)
ec2.delete_subnet(SubnetId=aws_resources['subnet_id'])
ec2.delete_route_table(RouteTableId=aws_resources['rtb_id'])
ec2.detach_internet_gateway(InternetGatewayId=aws_resources['igw_id'], VpcId=aws_resources['vpc_id'])
ec2.delete_internet_gateway(InternetGatewayId=aws_resources['igw_id'])
time.sleep(5)
ec2.delete_vpc(VpcId=aws_resources['vpc_id'])

