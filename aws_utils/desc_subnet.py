import boto3

client = boto3.client('ec2')

res = client.describe_subnets(
        SubnetIds = ['subnet-06c72b747bd512c00'],
        #SubnetIds = ['subnet-01e6d6eb53353839b'],
      )

print(res)
