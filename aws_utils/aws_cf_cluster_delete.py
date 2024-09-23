#!/usr/bin/env python3
import os
import pprint
import boto3
import sys

import pcluster.lib as pc

pp = pprint.PrettyPrinter()

cf_client = boto3.client('cloudformation')

stackname = 'Test-Cluster-2'

response = cf_client.delete_stack(
    StackName=stackname,
    DeletionMode='STANDARD'
)

waiter = cf_client.get_waiter('stack_delete_complete')

waiter.wait(
    StackName=stackname,
)
