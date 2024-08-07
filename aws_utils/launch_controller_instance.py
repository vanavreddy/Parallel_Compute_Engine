import boto3
import time
import os
import sys

# http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#service-resource

ec2 = boto3.resource('ec2')

'''
print(boto3.client('sts').get_caller_identity())#.get('UserName'))

username = None
try:
    iam = boto3.client('iam')
    username = iam.get_user()["User"]["UserName"]
except Exception as e:
    # The username is actually specified in the Access Denied message...
    print(e)
    #username = e.response["Error"]["Message"].split(" ")[-1]
print(username)

response = boto3.client('iam').list_roles()
for res in response['Roles']:
   if res['RoleName'] == 'ec2-ssm-role':
       print(res)
   time.sleep(1) 
#print(response)
'''

# create VPC
vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
# we can assign a name to vpc, or any resource, by using tag
vpc.create_tags(Tags=[{"Key": "Name", "Value": "vpc_controller"}])
vpc.wait_until_available()
print(vpc.id)

# create then attach internet gateway
ig = ec2.create_internet_gateway()
vpc.attach_internet_gateway(InternetGatewayId=ig.id)
print(ig.id)

# create a route table and a public route
route_table = vpc.create_route_table()
route = route_table.create_route(
    DestinationCidrBlock='0.0.0.0/0',
    GatewayId=ig.id
)
print(route_table.id)

# create subnet
subnet = ec2.create_subnet(CidrBlock='10.0.1.0/24', VpcId=vpc.id)
print(subnet.id)

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
    ],

)
print(sec_group.id)

# find image id ami-835b4efa / us-west-2
# Create instance
instances = ec2.create_instances(
    ImageId='ami-0c7217cdde317cfec', InstanceType='t2.large', MaxCount=1, MinCount=1, KeyName='controller_keypair',
    NetworkInterfaces=[{'SubnetId': subnet.id, 'DeviceIndex': 0, 'AssociatePublicIpAddress': True, 'Groups': [sec_group.group_id]}],
    BlockDeviceMappings=[{"DeviceName": "/dev/xvda","Ebs" : { "VolumeSize" : 500 }}],
    IamInstanceProfile={
                            'Arn': 'arn:aws:iam::672627884910:instance-profile/ec2-ssm-role',
                     },
#UserData = "#!/bin/bash\n    echo 'Hello World' > /home/ubuntu/hello.txt\n git clone https://github.com/vanavreddy/Benchmarking_Calorimeter_Shower_Simulation_Generative_AI.git\n sleep 10 \n mv /Benchmarking_Calorimeter_Shower_Simulation_Generative_AI /home/ubuntu\n chmod -R ugo+twx /home/ubuntu/Benchmarking_Calorimeter_Shower_Simulation_Generative_AI\n curl icanhazip.com > /home/ubuntu/controller_ip.txt \n cd /home/ubuntu \n wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \n bash /home/ubuntu/Miniconda3-latest-Linux-x86_64.sh -b > outmini.txt\n export PATH=$PATH:/opt/miniconda3:/opt/miniconda3/bin \n conda --version >> outmini.txt \n "
UserData = "#!/bin/bash\n    echo 'Hello World' > /home/ubuntu/hello.txt\n curl icanhazip.com > /home/ubuntu/controller_ip.txt \n"
)
instances[0].wait_until_running()
print(instances[0].id)
print("Root device: ", instances[0].root_device_name)

time.sleep(100)

instances[0].reload()

print(instances[0])

'''
with open('list.sh', 'r') as f:
  contents = f.read()

resp = boto3.client('ssm').send_command(
  InstanceIds=[instances[0].id],
  DocumentName='AWS-RunShellScript',
  Parameters={'commands': [f'echo "{contents}" > /home/ubuntu/file.sh']},
)
print(resp)

public_ip = instances[0].public_ip_address

print(public_ip)

bashCommand = "scp -i controller_keypair.pem -o StrictHostKeyChecking=no common.* ubuntu@"+public_ip+":/home/ubuntu/"
os.system(bashCommand)

'''

ip_address = instances[0].public_ip_address

bashCommand = "scp -i controller_keypair.pem -o StrictHostKeyChecking=no Unified_Epihiper_Pipeline_Setup.tar.gz ubuntu@"+ip_address+":/home/ubuntu/"
os.system(bashCommand)

time.sleep(10)

contents = ''
with open('aws_controller_setup.sh', 'r') as f:
  contents = f.read()

ssm = boto3.client('ssm')
instance_info = ssm.describe_instance_information().get('InstanceInformationList', {})[0]
cmd1 = "echo 'exporting script'"
cmd2 = 'whoami'
cmd3 = 'su - ubuntu'
cmd4 =  f'echo "{contents}" > /home/ubuntu/aws_controller_setup.sh'
cmd5 = 'sleep 10'
cmd6 = 'bash /home/ubuntu/aws_controller_setup.sh > /home/ubuntu/setup_output.txt 2>&1'
cmd7 = 'sleep 10'
#cmd8 = 'cat /home/ubuntu/setup_output.txt'
response = ssm.send_command(InstanceIds=[instances[0].id],
                            DocumentName='AWS-RunShellScript',
                            #Parameters={"commands": [cmd1, cmd2]}
                            Parameters={"commands":[cmd1, cmd3, cmd4, cmd5, cmd6, cmd7]}
                            )
command_id = response.get('Command', {}).get("CommandId", None)
while True:
    """ Wait for SSM response """
    response = ssm.list_command_invocations(CommandId=command_id, Details=True)
    """ If the command hasn't started to run yet, keep waiting """
    if len(response['CommandInvocations']) == 0:
        time.sleep(1)
        continue
    invocation = response['CommandInvocations'][0]
    if invocation['Status'] not in ('Pending', 'InProgress', 'Cancelling'):
        break
    time.sleep(1)
command_plugin = invocation['CommandPlugins'][-1]
output = command_plugin['Output']
print(f"Complete running, output: {output}")
