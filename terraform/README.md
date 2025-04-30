# EKS Cluster with Ollama GPU Instance and ECR Repositories Deployment Guide

This guide explains how to deploy an Amazon EKS cluster, an EC2 GPU instance running Ollama, and ECR repositories for Docker images using Terraform.

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

1. **Specify the key name in your `terraform.tfvars` file**:
   ```hcl
   ssh_key_name = "ollama-key"
   ```

The key is automatically created for you an saved under the terraform directory.

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

   **Note**: The deployment process may take 10-15 minutes to complete.

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

6. **Use ECR Repositories**:
   The deployment creates two ECR repositories for your Docker images:
   - `newsagent-api`: For the API service Docker image
   - `newsagent-django`: For the Django service Docker image
   
   You can use the `k8s/deploy.sh` script with the `--build` and `--push-to-ecr`, and `deploy` options to build and push the images:
   ```bash
   ./k8s/deploy.sh --build --push-to-ecr --deploy
   ```

## Cleaning Up

When you're done with the EKS cluster, you can clean up all resources to avoid incurring additional costs:

```bash
terraform destroy
```

Type `yes` when prompted to confirm the deletion of all resources.

**Note**: This will also delete the ECR repositories and any images stored in them. If you want to preserve your Docker images, you should back them up before running `terraform destroy`.

Alternatively, you can use the `k8s/deploy.sh` script with the `--delete` option to clean up Kubernetes resources and ECR repositories:
```bash
./k8s/deploy.sh --delete
```
