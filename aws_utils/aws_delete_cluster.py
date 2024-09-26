import argparse
import boto3
import sys
from aws_delete_controller import load_config

def delete_cluster(stack_name):
    # init cloudformation client
    cf_client = boto3.client('cloudformation')

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
    '''
    # get arguments
    parser = argparse.ArgumentParser(
                    prog='aws_delete_cluster.py',
                    description='Delete a cluster that was created with AWS CloudFormation stack',
                    )

    parser.add_argument('--stack_name', required=True, help='Name of the CloudFormation stack')

    args = parser.parse_args()
    '''

    # read in the environment variables
    dotenv_path = Path('../environment.sh')
    load_dotenv(dotenv_path=dotenv_path)
    AWS_CONFIG_DIR = os.environ["PIPELINE_ROOT"]+'/aws_setup_root'

    saved_cofig_file = AWS_CONFIG_DIR+'/saved_config.txt'

    with open(saved_cofig_file, 'w+') as f:
        f.write('stack_name:'+args.stack_name+'\n')

    aws_resources = load_config(saved_cofig_file)

    # delete cluster
    delete_cluster(aws_resources['stack_name'])

