# EKS Cluster with Ollama GPU Instance Deployment Guide

This guide explains how to deploy an Amazon EKS cluster and an EC2 GPU instance running Ollama using Terraform.

## Prerequisites

Before you begin, ensure you have the following:

1. **AWS Credentials** - You can provide these in two ways:
   - **Option 1:** Using the core/.env file (recommended)
   - **Option 2:** Using AWS CLI configured with appropriate credentials
2. **Terraform** (version 1.0.0 or later) installed
3. **kubectl** installed for interacting with the Kubernetes cluster
4. **AWS IAM permissions** to create EKS clusters, VPCs, and related resources

## Configuration Files

The Terraform configuration consists of the following files:

1. `main.tf` - Contains the actual resource definitions
2. `variables.tf` - Contains all customizable parameters with default values
3. `terraform.tfvars` - (Optional) Contains your specific variable values
   - You can copy the provided `terraform.tfvars.example` file to `terraform.tfvars` and customize it

## Customizing Your Deployment

All configuration is done through variables defined in `variables.tf`. You can set these variables in a `terraform.tfvars` file. Copy the example file to get started:

Edit the `terraform.tfvars` file to customize your deployment. The most common variables you might want to customize include:

```hcl
# AWS Region
aws_region = "us-west-2"

# Kubernetes Version
kubernetes_version = "1.32"

# Cluster Name
cluster_name = "my-eks-cluster"

# Node Group Configuration
node_instance_type = "t3.medium"
node_desired_size = 2
node_max_size = 3
node_min_size = 1

# Ollama Configuration
ollama_model = "mistral-nemo"
ollama_instance_name = "ollama-gpu-instance"
```

### SSH Key Pair Configuration

To SSH into the EC2 instance running Ollama, you need to create and specify an SSH key pair:

1. **Create an SSH key pair in AWS**:
   ```bash
   aws ec2 create-key-pair --key-name ollama-key --query 'KeyMaterial' --output text > ollama-key.pem
   chmod 400 ollama-key.pem
   ```

2. **Specify the key name in your `terraform.tfvars` file**:
   ```hcl
   ssh_key_name = "ollama-key"
   ```

If you don't specify an SSH key, the EC2 instance will still be created, but you won't be able to SSH into it directly. The Ollama service will still be installed and running, and EKS pods will be able to communicate with it.

## Deployment Steps

Follow these steps to deploy the EKS cluster:

1. **Initialize Terraform**:
   ```bash   
   terraform init
   ```

2. **Review the Deployment Plan**:
   ```bash
   terraform plan
   ```
   Review the plan to ensure it will create the resources you expect.

3. **Apply the Configuration**:
   ```bash
   terraform apply
   ```
   Type `yes` when prompted to confirm the deployment.

   **Note**: The deployment process may take 15-20 minutes to complete.

4. **Configure kubectl**:
   After the deployment completes, configure kubectl to connect to your new EKS cluster:
   ```bash
   aws eks update-kubeconfig --region <your-region> --name <your-cluster-name>
   ```
   Replace `<your-region>` with the AWS region and `<your-cluster-name>` with the cluster name you specified in your configuration.

5. **Verify the Cluster**:
   ```bash
   kubectl get nodes
   ```
   This should display the worker nodes that have joined the cluster.

6. **Connect to Ollama from EKS**:
   After deployment, Terraform will output the private IP address of the Ollama instance and instructions for connecting to it from your EKS pods. You can use this information to configure your applications to use the Ollama API.

   Example of connecting from a pod:
   ```bash
   kubectl run curl-test --image=curlimages/curl --rm -it -- \
     curl -X POST http://<ollama-private-ip>:11434/api/generate \
     -d '{"model": "mistral-nemo", "prompt": "Hello, world!"}'
   ```
   Replace `<ollama-private-ip>` with the private IP address output by Terraform.

7. **SSH into the Ollama Instance** (if you configured an SSH key):
   Since the Ollama instance is in a private subnet, you'll need to SSH through a bastion host or use AWS Systems Manager Session Manager. If you have a bastion host in the public subnet:
   ```bash
   # First, SSH to your bastion host
   ssh -i /path/to/bastion-key.pem ec2-user@<bastion-public-ip>
   
   # Then, from the bastion, SSH to the Ollama instance
   ssh -i /path/to/ollama-key.pem ubuntu@<ollama-private-ip>
   ```

## Cleaning Up

When you're done with the EKS cluster, you can clean up all resources to avoid incurring additional costs:

```bash
terraform destroy
```

Type `yes` when prompted to confirm the deletion of all resources.
