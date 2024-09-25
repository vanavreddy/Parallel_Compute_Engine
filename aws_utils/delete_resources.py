import boto3
import time
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def load_config(saved_cofig_file):
    aws_resources = {}
    with open(saved_cofig_file, 'r') as f:

        lines = f.readlines()
        for line in lines:
            line = line.strip()
            aws_resources[line.split(':')[0]] = line.split(':')[1]

    return aws_resources

def delete_controller_instance(aws_resources):
    ec2 = boto3.client('ec2')

    ec2.start_instances(InstanceIds=[aws_resources['instance_id']])
    time.sleep(60)
    ec2.terminate_instances(InstanceIds=[aws_resources['instance_id']])
    time.sleep(60)
    print(f"Terminated controller instance: {aws_resources['instance_id']}")

    ec2.delete_security_group(GroupId=aws_resources['sec_group_id'])
    time.sleep(5)
    print(f"Deleted security group: {aws_resources['sec_group_id']}")

    ec2.delete_subnet(SubnetId=aws_resources['subnet_id'])
    time.sleep(5)
    print(f"Deleted subnet: {aws_resources['subnet_id']}")

    ec2.delete_route_table(RouteTableId=aws_resources['rtb_id'])
    print(f"Deleted routing table: {aws_resources['rtb_id']}")

    ec2.detach_internet_gateway(InternetGatewayId=aws_resources['igw_id'], VpcId=aws_resources['vpc_id'])
    ec2.delete_internet_gateway(InternetGatewayId=aws_resources['igw_id'])
    time.sleep(5)
    print(f"Deleted internet gateway: {aws_resources['igw_id']}")

    ec2.delete_vpc(VpcId=aws_resources['vpc_id'])
    print(f"Deleted VPC: {aws_resources['vpc_id']}")

if __name__ == "__main__":
    # read in the environment variables
    dotenv_path = Path('../environment.sh')
    load_dotenv(dotenv_path=dotenv_path)
    AWS_CONFIG_DIR = os.environ["PIPELINE_ROOT"]+'/aws_setup_root'
    saved_cofig_file = AWS_CONFIG_DIR+'/saved_config.txt'

    aws_resources = load_config(saved_cofig_file)
    delete_controller_instance(aws_resources)
