# Setup a HPC cluster on Amazon AWS and run the modeling pipeline on the AWS cluster.

You will need an AWS account, preferably one setup through UVA ITS folks. 
Once the account is ready,  make sure you can login and that you have 
AdministrationAccess privileges, to create and launch instances.

## Create key-pair

There are multiple ways to create the kep-pair, 
follow the [link](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html) 
for more details. Instructions below are adapted from this [link](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html) .

After you login, navigate to [EC2 dashboard](https://console.aws.amazon.com/ec2). 
To create a key pair using Amazon EC2

1. In the navigation pane, under Network & Security, choose Key Pairs.
2. Choose Create key pair.
3. For Name, enter a descriptive name for the key pair. Amazon EC2 associates the public key 
with the name that you specify as the key name. A key name can include up to 255 ASCII characters. 
It can’t include leading or trailing spaces.
5. For Key pair type, choose either RSA or ED25519.
6. For Private key file format, choose the format in which to save the private key. 
To save the private key in a format that can be used with OpenSSH, choose pem. 
To save the private key in a format that can be used with PuTTY, choose ppk.
7. To add a tag to the public key, choose Add tag, and enter the key and value for the tag. Repeat for each tag.
8. Choose Create key pair.
9. The private key file is automatically downloaded by your browser. The base file name is 
the name that you specified as the name of your key pair, and the file name extension is 
determined by the file format that you chose. Save the private key file in a safe place.

Important
This is the only chance for you to save the private key file.
If you plan to use an SSH client on a macOS or Linux computer to connect to your Linux 
instance, use the following command to set the permissions of your private key file so that only you can read it.

```
chmod 400 key-pair-name.pem
```

If you do not set these permissions, then you cannot connect to your instance using this key pair. 

## Install AWS ParallelCluster in a virtual environment 

It is recommended to install AWS ParallelCluster in a virtual environment to 
avoid requirement version conflicts with other pip packages.

```
$ conda env create -f conda_env_files/aws_env.yml
$ conda activate aws_env
```

Install Node Version Manager with the lastest Long-Term Support (TS) Node.js version.

```
$ curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
$ chmod ug+x ~/.nvm/nvm.sh
$ source ~/.nvm/nvm.sh
$ nvm install --lts
$ node --version
v20.15.1
```

Install AWS ParallelCluster packages
```
$ pip install aws-parallelcluster
```

Verify that AWS ParallelCluster is installed correctly.

```
$ pcluster version
{
  "version": "3.10.1"
}
```

To upgrade to the latest version of AWS ParallelCluster, run the installation command again.

```
$ pip install --upgrade aws-parallelcluster
```

Install the AWS Command Line Interface tools.

```
$ pip install awscli
```

You can use the "conda deactivate" deactivate command to exit the virtual environment. 
Each time you start a session, you must reactivate the environment.

For additional details, refer to [AWS resource](https://docs.aws.amazon.com/parallelcluster/latest/ug/install-v3-virtual-environment.html).

## Configure and create a cluster with the AWS ParallelCluster command line interface

The steps given below are generic and serve only as an example. 
Customize the steps to suit your specific requirements.

1. Authenticate using AWS session information
2. Configure and create the AWS HPC cluster
3. Setup Epihiper setup utils on the AWS HPC cluster's headnode

### Authenticate using AWS session information

To authenticate and create a session, we need to get the credentials for AdministratorAccess. 
UVA ITS would provide a specific link to login to AWS admin console. Use this link to authenticate. 
Once authenticated, you will need "AWS Access Key ID", "AWS Secret Access Key
" and "AWS Session Token". This information can be retieved by clicking on 
"Command line and programmatic access" after you login to the AWS admin console. 

```
$ export AWS_ACCESS_KEY_ID="copy-string-from-Command-line-and-programmatic-access"
$ export AWS_SECRET_ACCESS_KEY="copy-string-from-Command-line-and-programmatic-access"
$ export AWS_SESSION_TOKEN="copy-string-from-Command-line-and-programmatic-access"
```

Now, your credentials are established. Additionally, you may want to explore 
**aws configure** and **aws configure sso** options 
[here](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html).

### Configure and create the AWS HPC cluster

The steps to configure AWS cluster are slightly involved requiring the user 
to make choices based on the type of cluster resources and other details 
specific to their AWS account. Follow this [link](https://docs.aws.amazon.com/parallelcluster/latest/ug/install-v3-configuring.html) 
for more information. 

Create your first cluster by using the **pcluster configure** CLI command to initiate 
a wizard that prompts you for all of the information that's required to configure 
and create your cluster. The details of the sequence differ when using AWS Batch 
as the scheduler compared to using Slurm.

```
$  pcluster configure --config my-config-file.yaml

INFO: Configuration file my-config-file.yaml will be written.
Press CTRL-C to interrupt the procedure.

Allowed values for AWS Region ID:
1. ap-northeast-1
2. ap-northeast-2
3. ap-south-1
4. ap-southeast-1
5. ap-southeast-2
6. ca-central-1
7. eu-central-1
8. eu-north-1
9. eu-west-1
10. eu-west-2
11. eu-west-3
12. sa-east-1
13. us-east-1
14. us-east-2
15. us-west-1
16. us-west-2
AWS Region ID [us-east-1]: 13

# Here, to select **us-east-1**, enter **13** at the prompt.
```

The key pair is selected from the key pairs that are registered with Amazon EC2 in the selected AWS Region.
If you have multiple key-pairs, select one of the key-pairs you created in the earlier step.

```
Allowed values for EC2 Key Pair Name:
1. poc-hpc-cluster
EC2 Key Pair Name [poc-hpc-cluster]: 1
```

Choose the scheduler to use for your HPC cluster.

```
Allowed values for Scheduler:
1. slurm
2. awsbatch
Scheduler [slurm]: 1

# Here, to select "slurm", enter **1** at the prompt.
```

Choose the operating system.

```
Allowed values for Operating System:
1. alinux2
2. centos7
3. ubuntu2004
4. ubuntu2204
5. rhel8
6. rocky8
Operating System [alinux2]: 3

# Here, to select "ubuntu2004", enter **3** at the prompt.
```

Choose head node instance type, for list of instances refer to [AWS instance types](https://aws.amazon.com/ec2/instance-types/).

```
Head node instance type [t2.micro]: hpc7g.4xlarge
```

Choose the queue configuration. Note: Instance type can't be specified
for multiple compute resources in the same queue.

``` 
Number of queues [1]: 1
Name of queue 1 [queue1]: bii-testq
Number of compute resources for queue1 [1]: 1
Compute instance type for compute resource 1 in queue1 [t2.micro]: hpc7g.4xlarge
```

Enable EFA to run applications that require high levels of inter-instance
communication at scale on AWS at no additional charge

```
The EC2 instance selected supports enhanced networking capabilities using Elastic Fabric Adapter (EFA). EFA enables you to run applications requiring high levels of inter-node communications at scale on AWS at no additional charge (https://docs.aws.amazon.com/parallelcluster/latest/ug/efa-v3.html).
Enable EFA on hpc7g.4xlarge (y/n) [y]: y
Maximum instance count [10]: 10
Placement Group name []:

# Here, press **enter** or **return** to leave group name blank.
```

After the previous steps are completed, decide whether to use an existing VPC or
let AWS ParallelCluster create a VPC for you. If you don't have a properly configured VPC,
AWS ParallelCluster can create a new one for you.

```
Automate VPC creation? (y/n) [n]: y
Allowed values for Availability Zone:
1. us-east-1d
Availability Zone [us-east-1d]: 1
Allowed values for Network Configuration:
1. Head node in a public subnet and compute fleet in a private subnet
2. Head node and compute fleet in the same public subnet
Network Configuration [Head node in a public subnet and compute fleet in a private subnet]: 1
Beginning VPC creation. Please do not leave the terminal until the creation is finalized
```

Subnet creation
```
Automate Subnet creation? (y/n) [y]: y

Creating CloudFormation stack...
Do not leave the terminal until the process has finished
```

Check the status of the cluster creation.

```
$ pcluster create-cluster --cluster-name my-test-cluster --cluster-configuration my-config-file.yaml
{
  "cluster": {
    "clusterName": "my-test-cluster",
    "cloudformationStackStatus": "CREATE_IN_PROGRESS",
    "cloudformationStackArn": "arn:aws:cloudformation:eu-west-1:xxx:stack/test-cluster/abcdef0-f678-890ac-021345cdef",
    "region": "eu-west-1",
    "version": "3.8.0",
    "clusterStatus": "CREATE_IN_PROGRESS"
  },
  "validationMessages": []
}

```

After successful completion of the above steps, a yaml file named **my-config-file.yaml** will be automatically saved in the current directory on your local machine. This file can be reused to create AWS HPC cluster of the same configuration as above in the future. 

```
# Create a cluster using saved yaml file

$ pcluster create-cluster --cluster-configuration my-config-file.yml --cluster-name <cluster-name> --region us-east-1

# This step may take several minutes to finish.
```

The sample config file (**sample-config-file.yml**) can be used to create a simple cluster with one head node two compute nodes. Change the following fields to your specific AWS account information in sample-config-file.yml, SubnetId: **subnet-06c72b747bd512c00**, Ssh: KeyName: **poc-hpc-cluster** and SubnetIds: - **subnet-003546501b9666644**.

```
$ pcluster create-cluster --cluster-configuration sample-config-file.yml --cluster-name bii-hpc-cluster --region us-east-1

# Check the status of the cluster

$ pcluster describe-cluster --cluster-name bii-hpc-cluster
```

Once the cluster is created, login to the headnode, you will need youe key-pair information.

```
$ ssh --cluster-name bii-hpc-cluster -i <local-path>/key-pair-name.pem
```

 After successful login to head node, install the packages needed to run EpiHiper-Code

```
# Clone EpiHiper code from git
git clone git@github.com:NSSAC/EpiHiper-code.git

# Install required packages

$ sudo apt-get -y update
$ sudo apt-get install libpq-dev postgresql-server-dev-all
$ sudo apt-get install -y libpq5
```

