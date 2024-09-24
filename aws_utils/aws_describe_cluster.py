import argparse
import boto3
import sys

def describe_cluster(args):
    # init cloudformation client
    cf_client = boto3.client('cloudformation')

    stack_name = args.stack_name

    # command to delete cluster
    response = cf_client.describe_stacks(
        StackName=stack_name,
    )

    print(response)

if __name__ == "__main__":
    # get arguments
    parser = argparse.ArgumentParser(
                    prog='aws_describe_cluster.py',
                    description='Describe cluster that was created with AWS CloudFormation stack',
                    )

    parser.add_argument('--stack_name', required=True, help='Name of the CloudFormation stack')

    args = parser.parse_args()

    # decribe cluster
    describe_cluster(args)

