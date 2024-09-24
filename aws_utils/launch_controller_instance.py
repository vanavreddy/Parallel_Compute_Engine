import boto3
import time
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

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

        # create VPC
        vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
        # we can assign a name to vpc, or any resource, by using tag
        vpc.create_tags(Tags=[{"Key": "Name", "Value": "vpc_controller"}])
        vpc.wait_until_available()
        print(vpc.id)

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
        subnet = ec2.create_subnet(CidrBlock='10.0.1.0/24', VpcId=vpc.id)
        print(subnet.id)

        f.write('subnet_id:'+subnet.id+'\n')

        # associate the route table with the subnet
        route_table.associate_with_subnet(SubnetId=subnet.id)

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
        print(sec_group.id)

        f.write('sec_group_id:'+sec_group.id+'\n')

        # find image id ami-835b4efa / us-west-2
        # Create instance
        user_data = "#!/bin/bash\n    echo 'Hello World' > /home/ubuntu/hello.txt\n curl icanhazip.com > /home/ubuntu/controller_ip.txt \n shutdown -P +"+str(sd_in_minutes)

        instances = ec2.create_instances(
            ImageId='ami-0c7217cdde317cfec', InstanceType='t2.large', MaxCount=1, MinCount=1, KeyName='controller_keypair',
            NetworkInterfaces=[{'SubnetId': subnet.id, 'DeviceIndex': 0, 'AssociatePublicIpAddress': True, 'Groups': [sec_group.group_id]}],
            BlockDeviceMappings=[{"DeviceName": "/dev/xvda","Ebs" : { "VolumeSize" : 500 }}],
            IamInstanceProfile={
                            'Arn': 'arn:aws:iam::672627884910:instance-profile/ec2-ssm-role',
                     },
            UserData = user_data
        )
        instances[0].wait_until_running()
        print(instances[0].id)

        time.sleep(100)

        instances[0].reload()

        print(instances[0])
        f.write('instance_id:'+instances[0].id)


    ip_address = instances[0].public_ip_address
    with open(PIPELINE_ROOT+'/controller_ip.txt', 'w+') as f1:
        f1.write(ip_address+'\n')

    scpCommand = "scp -i "+AWS_CONFIG_DIR+"/controller_keypair.pem -o StrictHostKeyChecking=no "+AWS_CONFIG_DIR+"/common.* ubuntu@"+ip_address+":/home/ubuntu/"
    os.system(scpCommand)

    time.sleep(10)

    controller_contents = ''
    with open('../aws_utils/aws_controller_setup.sh', 'r') as f:
        controller_contents = f.read()

    conda_contents = ''
    with open('../aws_utils/conda_env_setup.sh', 'r') as f:
        conda_contents = f.read()

    file_name = '../aws_utils/aws_controller_setup.sh'
    scpCommand = "scp -i "+AWS_CONFIG_DIR+"/controller_keypair.pem -o StrictHostKeyChecking=no "+file_name+" ubuntu@"+ip_address+":/home/ubuntu/"
    os.system(scpCommand)
    file_name = '../aws_utils/conda_env_setup.sh'
    scpCommand = "scp -i "+AWS_CONFIG_DIR+"/controller_keypair.pem -o StrictHostKeyChecking=no "+file_name+" ubuntu@"+ip_address+":/home/ubuntu/"
    os.system(scpCommand)

    ssm = boto3.client('ssm')
    instance_info = ssm.describe_instance_information().get('InstanceInformationList', {})[0]
    cmd10 = 'bash /home/ubuntu/conda_env_setup.sh'
    response = ssm.send_command(InstanceIds=[instances[0].id],
                            DocumentName='AWS-RunShellScript',
                            Parameters={"commands":[cmd10]}
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

