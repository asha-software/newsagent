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
2. `variables.tf` - Contains all customizable parameters with their types and default values
3. `terraform.tfvars` - Contains your specific variable values that override the defaults in variables.tf

### Understanding variables.tf vs terraform.tfvars

- **variables.tf**: Defines all the variables that can be used in the Terraform configuration, including their types, descriptions, and default values. This file serves as documentation for what variables are available and what they do.

- **terraform.tfvars**: Provides actual values for the variables defined in variables.tf. Values in this file override the default values in variables.tf. This separation allows you to keep your specific configuration separate from the variable definitions.

This is standard Terraform practice that allows for flexibility and reusability of the configuration.

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

The key is automatically created for you and saved under the terraform directory.

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
   terraform apply (optional --auto-approve)
   ```
   Type `yes` when prompted to confirm the deployment.

   **Note**: The deployment process may take 10-15 minutes to complete.

4. **Configure Secrets**:
   After Terraform has created the infrastructure, you need to configure the application secrets:
   ```bash
   # Copy the template file to create your own secrets file
   cp k8s/base/secrets/app-secrets.template.yaml k8s/base/secrets/app-secrets.yaml
   ```
   
   Edit the `app-secrets.yaml` file to replace the placeholder values with your actual credentials and add LLM model settings.

5. **Verify the Cluster**:
   ```bash
   kubectl get nodes
   ```
   This should display the worker nodes that have joined the cluster.

## Deployment Order and Integration with k8s/deploy.sh

The correct order for deploying the entire application is:

1. **Run Terraform to create infrastructure**:
   ```bash
   cd terraform
   terraform init
   terraform apply
   ```
   This creates the EKS cluster, ECR repositories, and Ollama EC2 instance.

2. **Configure Secrets**:
   ```bash
   cp k8s/base/secrets/app-secrets.template.yaml k8s/base/secrets/app-secrets.yaml
   # Edit app-secrets.yaml with your credentials and settings
   ```

3. **Use the k8s/deploy.sh script for the remaining steps**:
   ```bash
   # Build Docker images
   ./k8s/deploy.sh --build
   
   # Push images to ECR
   ./k8s/deploy.sh --push-to-ecr
   
   # Deploy to Kubernetes
   ./k8s/deploy.sh --deploy
   ```

**Important Note**: Do not use the `--terraform` flag with `--push-to-ecr` in the same command. The `--push-to-ecr` flag attempts to create ECR repositories if they don't exist, but Terraform has already created these repositories. This can cause conflicts and errors. Always run Terraform separately first, then proceed with the other steps.

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

## Troubleshooting

### Common Issues

1. **Terraform state lock issues**:
   If Terraform fails with a state lock error, you may need to manually release the lock:
   ```bash
   terraform force-unlock <LOCK_ID>
   ```

2. **AWS credential issues**:
   Ensure your AWS credentials are properly configured either in core/.env or through the AWS CLI.

3. **Resource creation failures**:
   - Check the AWS console for more details about the failure
   - Ensure you have sufficient permissions to create all required resources
   - Verify that you're not hitting any AWS service limits

4. **ECR repository conflicts**:
   If you encounter errors about ECR repositories already existing:
   - Ensure you're not trying to create repositories that already exist
   - Use the AWS console to check the status of existing repositories
   - If needed, delete existing repositories before recreating them
