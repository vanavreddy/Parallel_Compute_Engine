import boto3
import time
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

def create_vpc(ec2):
    # create VPC
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    # we can assign a name to vpc, or any resource, by using tag
    vpc.create_tags(Tags=[{"Key": "Name", "Value": "vpc_controller"}])
    vpc.wait_until_available()
    print(f"Created VPC : {vpc.id}")

    return vpc

def create_internet_gateway(ec2, vpc):
    # create then attach internet gateway
    ig = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=ig.id)
    print(f"Created internet gateway: {ig.id}")

    return ig

def create_routing_table(vpc, ig):
    # create a route table and a public route
    route_table = vpc.create_route_table()
    route = route_table.create_route(
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=ig.id
    )
    print(f"Created routing table: {route_table.id}")

    return route_table

def create_subnet(ec2, vpc, route_table):
    # create subnet
    subnet = ec2.create_subnet(CidrBlock='10.0.1.0/24', VpcId=vpc.id)

    # associate the route table with the subnet
    route_table.associate_with_subnet(SubnetId=subnet.id)
    print(f"Created subnet: {subnet.id}")

    return subnet

def create_security_group(ec2, vpc):
    # Create sec group
    sec_group = ec2.create_security_group(
        GroupName='sg_controller', Description='slice_0 sec group', VpcId=vpc.id)

    sec_group.authorize_ingress(
        IpPermissions=[
        {
            "FromPort": 22,
            "ToPort": 22,
            "IpProtocol": "tcp",
                "IpRanges": [
            {"CidrIp": "0.0.0.0/0", "Description": "internet"},
            ],
        },
        {
            "FromPort": 80,
            "ToPort": 80,
            "IpProtocol": "tcp",
            "IpRanges": [
                {"CidrIp": "0.0.0.0/0", "Description": "internet"},
            ],
        },
        {
            "FromPort": -1,
            "ToPort": -1,
            "IpProtocol": "icmp",
            "IpRanges": [
             {"CidrIp": "0.0.0.0/0", "Description": "internet"},
            ],
        },
        {
            "FromPort": -1,
            "ToPort": -1,
            "IpProtocol": "-1",
            "IpRanges": [
             {"CidrIp": "0.0.0.0/0", "Description": "all traffic"},
            ],
        },
    ],
    )
    print(f"Created security group: {sec_group.id}")

    return sec_group

def create_instance(ec2, subnet, sec_group):
    # Create instance
    instances = ec2.create_instances(
        ImageId='ami-0c7217cdde317cfec', InstanceType='t2.large', MaxCount=1, MinCount=1, KeyName='controller_keypair',
        NetworkInterfaces=[
            {   'SubnetId': subnet.id, 
                'DeviceIndex': 0, 
                'AssociatePublicIpAddress': True, 
                'Groups': [sec_group.group_id]
            }
        ],
        BlockDeviceMappings=[
            {   "DeviceName": "/dev/xvda", 
                "Ebs" : { "VolumeSize" : 500 }
            }
        ],
        IamInstanceProfile={
            'Arn': 'arn:aws:iam::672627884910:instance-profile/ec2-ssm-role',
        },
    )
    instances[0].wait_until_running()
    print(f"Creating instance...")
    time.sleep(100)
    instances[0].reload()

    print(f"Created instance: {instances[0].id}")

    return instances[0]


def launch_controller(args):
    # read in the environment variables
    dotenv_path = Path('../environment.sh')
    load_dotenv(dotenv_path=dotenv_path)
    LOG_DIR = os.environ["LOG_DIR"]
    SETUP_DIR = os.environ["SETUP_DIR"]
    TIMELIMIT = os.environ["MAX_RUNTIME"]
    AWS_CONFIG_DIR = os.environ["PIPELINE_ROOT"]+'/aws_setup_root'
    PIPELINE_ROOT= os.environ["PIPELINE_ROOT"]
    sd_in_minutes = int(TIMELIMIT.split(':')[0])*60*60 + int(TIMELIMIT.split(':')[1])*60 + int(TIMELIMIT.split(':')[2])

    saved_cofig_file = AWS_CONFIG_DIR+'/saved_config.txt'

    ec2 = boto3.resource('ec2')

    with open(saved_cofig_file, 'w+') as f:

        vpc = create_vpc(ec2)
        f.write('vpc_id:'+vpc.id+'\n')

        ig = create_internet_gateway(ec2, vpc)
        f.write('igw_id:'+ig.id+'\n')


        route_table = create_routing_table(vpc, ig)
        f.write('rtb_id:'+route_table.id+'\n')


        subnet = create_subnet(ec2, vpc, route_table)
        f.write('subnet_id:'+subnet.id+'\n')

        sec_group = create_security_group(ec2, vpc)
        f.write('sec_group_id:'+sec_group.id+'\n')


        instance = create_instance(ec2, subnet, sec_group)
        f.write('instance_id:'+instance.id)

    # save the public ip address to connect later
    ip_address = instance.public_ip_address
    with open(PIPELINE_ROOT+'/controller_ip.txt', 'w+') as f1:
        f1.write(ip_address+'\n')

    # copy keypar to the instance
    scpCommand = "scp -i "+AWS_CONFIG_DIR+"/controller_keypair.pem -o StrictHostKeyChecking=no "+AWS_CONFIG_DIR+"/common.* ubuntu@"+ip_address+":/home/ubuntu/"
    os.system(scpCommand)

    '''
    # read contents of the controller setup file
    controller_contents = ''
    with open('../aws_utils/aws_controller_setup.sh', 'r') as f:
        controller_contents = f.read()

    # read contents of the setup file
    conda_contents = ''
    with open('../aws_utils/conda_env_setup.sh', 'r') as f:
        conda_contents = f.read()

    file_name = '../aws_utils/aws_controller_setup.sh'
    scpCommand = "scp -i "+AWS_CONFIG_DIR+"/controller_keypair.pem -o StrictHostKeyChecking=no "+file_name+" ubuntu@"+ip_address+":/home/ubuntu/"
    os.system(scpCommand)
    file_name = '../aws_utils/conda_env_setup.sh'
    scpCommand = "scp -i "+AWS_CONFIG_DIR+"/controller_keypair.pem -o StrictHostKeyChecking=no "+file_name+" ubuntu@"+ip_address+":/home/ubuntu/"
    os.system(scpCommand)
    '''

    print("Setting up the conda environment in the new controller instance...")

    # run conda setup script on the newly created instance
    ssm = boto3.client('ssm')
    instance_info = ssm.describe_instance_information().get('InstanceInformationList', {})[0]
    cmd1 = 'bash /home/ubuntu/Parallel_Compute_Engine/aws_utils/conda_env_setup.sh'
    #cmd2 = 'bash /home/ubuntu/Parallel_Compute_Engine/aws_utils/run_aws_controller.sh'
    response = ssm.send_command(InstanceIds=[instances[0].id],
                            DocumentName='AWS-RunShellScript',
                            #Parameters={"commands":[cmd1, cmd2]}
                            Parameters={"commands":[cmd1]}
                            )
    command_id = response.get('Command', {}).get("CommandId", None)

    while True:
        """ Wait for SSM response """
        response = ssm.list_command_invocations(CommandId=command_id, Details=True)
        """ If the command hasn't started to run yet, keep waiting """
        if len(response['CommandInvocations']) == 0:
            time.sleep(5)
            continue
        invocation = response['CommandInvocations'][0]
        if invocation['Status'] not in ('Pending', 'InProgress', 'Cancelling'):
            break
        time.sleep(5)

    command_plugin = invocation['CommandPlugins'][-1]
    output = command_plugin['Output']
    print(f"Completed running SSM command, output: {output}\n")

    print("Next Step: Login to the intance and finish setting up the controller.")
    print("\nTo SSH to the controller instance, use the command below,")
    print("\nssh -i "+AWS_CONFIG_DIR+"/controller_keypair.pem ubuntu@"+ip_address)
    print("\n\n")


if __name__ == "__main__":
    # get arguments
    parser = argparse.ArgumentParser(
                    prog='aws_launch_controller.py',
                    description='Launch controller instance using AWS EC2',
                    )

    parser.add_argument('--key_name', required=False, help='path to Keypair file')

    args = parser.parse_args()

    # launch controller
    launch_controller(args)

