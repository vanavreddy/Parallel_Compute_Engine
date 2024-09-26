import boto3
import argparse
import sys

def create_cluster(args):
    # init cloudformation client
    cf_client = boto3.client('cloudformation')

    stack_name = args.stack_name
    instance_count = args.instance_count
    key_name = args.key_name

    # read the cloutformation template file and create cluster
    with open('cloudstack_cluster.yaml', 'r') as cf_file:

        cft_template = cf_file.read()

        # modifiable parameters
        params = [{"ParameterKey": "KeyName", "ParameterValue": key_name}, {"ParameterKey": "InstanceCount", "ParameterValue": instance_count}]
        # capabilities
        capabs = ['CAPABILITY_NAMED_IAM','CAPABILITY_AUTO_EXPAND']

        # create cluster
        cf_client.create_stack(StackName=stack_name, TemplateBody=cft_template, Parameters=params, Capabilities=capabs)

    # init waiter
    waiter = cf_client.get_waiter('stack_create_complete')

    # wait until the cluster is created
    waiter.wait(
        StackName=stack_name,
    )

if __name__ == "__main__":
    # get arguments
    parser = argparse.ArgumentParser(
                    prog='aws_create_cluster.py',
                    description='Creates a cluster using AWS CloudFormation stack',
                    )

    parser.add_argument('--key_name', required=True, help='path to Keypair file')
    parser.add_argument('--stack_name', required=True, help='Name of the CloudFormation stack')
    parser.add_argument('--instance_count', required=True, help='Number of compute node instances in the cluster')

    args = parser.parse_args()

    # read in the environment variables
    dotenv_path = Path('../environment.sh')
    load_dotenv(dotenv_path=dotenv_path)
    AWS_CONFIG_DIR = os.environ["PIPELINE_ROOT"]+'/aws_setup_root'

    saved_cofig_file = AWS_CONFIG_DIR+'/saved_config.txt'

    with open(saved_cofig_file, 'w+') as f:
        f.write('stack_name:'+args.stack_name+'\n')

    # create cluster
    create_cluster(args)

