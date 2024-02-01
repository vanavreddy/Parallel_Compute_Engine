# Steps to setup a HPC cluster on AWS resources and run the modeling pipeline on the cluster.

You will need an AWS account, preferably one setup through UVA ITS folks. 
Once the account is ready,  make sure you can login and that you have 
AdministrationAccess privileges, e.g., to create and launch instances.

## Create key-pair

There are multiple ways to create the kep-pair, 
follow the [link](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html) 
for more details. Instructions below are adapted from [link](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html) .

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

If you do not set these permissions, then you cannot connect to your instance using this key pair. For more information, see Error: Unprotected private key file.















Step2: Install python and other packages on your local system (to use CLI interface)

Step3: Create a virtualenv
https://docs.aws.amazon.com/parallelcluster/latest/ug/install-v3-virtual-environment.html

Step4: Install AWS ParallelCluster into your virtual environment.

https://docs.aws.amazon.com/parallelcluster/latest/ug/install-v3-virtual-environment.html

Step5: Getting started - creating the cluster

https://docs.aws.amazon.com/parallelcluster/latest/ug/install-v3-configuring.html

aws configure sso
SSO session name (Recommended): bii-aws-hpc
SSO start URL [None]: https://eservices-uva.awsapps.com/start/
SSO region [None]: us-east-1
SSO registration scopes [sso:account:access]:
Attempting to automatically open the SSO authorization page in your default browser.
If the browser does not open or you wish to use a different device to authorize this request, open the following URL:

https://device.sso.us-east-1.amazonaws.com/

Then enter the code:

LHDW-WGSR
The only AWS account available to you is: 672627884910
Using the account ID 672627884910
The only role available to you is: AdministratorAccess
Using the role name "AdministratorAccess"
CLI default client Region [us-east-1]:
CLI default output format [None]:
CLI profile name [AdministratorAccess-672627884910]:

To use this profile, specify the profile name using --profile, as shown:

aws s3 ls --profile AdministratorAccess-672627884910

On Cluster headnode

Copy EpiHiper code
sudo apt-get -y update
sudo apt-get install libpq-dev postgresql-server-dev-all
sudo apt-get install -y libpq5

Cluster building Options

Option-1: Create a cluster from default image types and customize as needed. 
	- This involves installing the required packages on the head and compute nodes.
	- Copying the required data to the head node (EpiHiper code, DB cache etc)
	- Running the EpiHiper code

Option-2: Create a cluster from custom image
	- Build a custom image (for head and compute nodes) with required packages installed (steps below - Building custom AMIs)
	- Attach the volume where data is copied and saved as snapshot
	- Running the EpiHiper code

