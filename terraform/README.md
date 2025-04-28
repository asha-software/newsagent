# Simplified EKS Cluster Deployment Guide

This guide explains how to deploy an Amazon EKS cluster using Terraform.

## Prerequisites

Before you begin, ensure you have the following:

1. **AWS Credentials** - You can provide these in two ways:
   - **Option 1:** Using the core/.env file (recommended)
   - **Option 2:** Using AWS CLI configured with appropriate credentials
2. **Terraform** (version 1.0.0 or later) installed
3. **kubectl** installed for interacting with the Kubernetes cluster
4. **AWS IAM permissions** to create EKS clusters, VPCs, and related resources

## Configuration Files

The Terraform configuration consists of two main files:

1. `main.tf` - Contains the actual resource definitions
2. `variables.tf` - Contains all customizable parameters with default values

## Customizing Your Deployment

All configuration is done through variables defined in `variables.tf`. The most common variables you might want to customize include:

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
```

## Deployment Steps

Follow these steps to deploy the EKS cluster:

1. **Initialize Terraform**:
   ```bash
   # If using core/.env file:
   ./run_terraform.sh init
   
   # If using AWS CLI:
   terraform init
   ```

2. **Review the Deployment Plan**:
   ```bash
   # If using core/.env file:
   ./run_terraform.sh plan
   
   # If using AWS CLI:
   terraform plan
   ```
   Review the plan to ensure it will create the resources you expect.

3. **Apply the Configuration**:
   ```bash
   # If using core/.env file:
   ./run_terraform.sh apply
   
   # If using AWS CLI:
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

## Cleaning Up

When you're done with the EKS cluster, you can clean up all resources to avoid incurring additional costs:

```bash
# If using core/.env file:
./run_terraform.sh destroy

# If using AWS CLI:
terraform destroy
```

Type `yes` when prompted to confirm the deletion of all resources.
