import os
import argparse
import boto3
import sys

def delete_cluster(args):
    cf_client = boto3.client('cloudformation')

    stack_name = args.stack_name

    # command to delete cluster
    response = cf_client.delete_stack(
        StackName=stack_name,
        DeletionMode='STANDARD'
    )

    # waiter
    waiter = cf_client.get_waiter('stack_delete_complete')

    # wait until the cluster is delete
    waiter.wait(
        StackName=stack_name,
    )

if __name__ == "__main__":
    # get arguments
    parser = argparse.ArgumentParser(
                    prog='aws_cf_delete_cluster.py',
                    description='Delete a cluster that was created with AWS CloudFormation stack',
                    )

    parser.add_argument('--stack_name', required=True, help='Name of the CloudFormation stack')

    args = parser.parse_args()

    # delete cluster
    delete_cluster(args)

