# NewsAgent: Kubernetes and Terraform Deployment Guide

This guide explains how to deploy the NewsAgent application using Terraform for infrastructure provisioning and Kubernetes for application deployment.

## System Components

The NewsAgent application consists of:

1. **Infrastructure (provisioned by Terraform)**:
   - Amazon EKS (Elastic Kubernetes Service) cluster
   - ECR (Elastic Container Registry) repositories for Docker images
   - EC2 GPU instance running Ollama for LLM inference

2. **Application (deployed to Kubernetes)**:
   - MySQL Database (using the official mysql:8.0 image)
   - Django Web Application
   - FastAPI Application (API)

## Prerequisites

Before deploying, ensure you have:

1. **AWS Credentials** - You can provide these in two ways:
   - **Option 1:** Using the core/.env file (recommended)
   - **Option 2:** Using AWS CLI configured with appropriate credentials
2. **Terraform** (version 1.0.0 or later) installed
3. **kubectl** installed and configured
4. **AWS CLI** installed and configured
5. **Docker** installed (for building images)

## Deployment Process

You can deploy the NewsAgent application either locally using Docker Compose or to AWS using Kubernetes and Terraform.

### Local Deployment with Docker Compose

For local development or testing, you can use Docker Compose:

```bash
# Start all services locally
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f
```

This will start the MySQL database, Django web application, and FastAPI service on your local machine.

#### Local Environment Configuration

For local deployment, you can configure the application using environment variables in a `.env` file or by setting them directly in the `docker compose.yml` file. The main environment variables include:

```
# Database configuration
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=fakenews_db
MYSQL_USER=fakenews_user
MYSQL_PASSWORD=password

# API configuration
DB_HOST=db
DB_NAME=fakenews_db
DB_USER=fakenews_user
DB_PASSWORD=password
API_URL=http://api:8000

# LLM configuration
CLAIM_DECOMPOSER_MODEL=mistral-nemo
RESEARCH_AGENT_MODEL=mistral-nemo
REASONING_AGENT_MODEL=mistral-nemo
VERDICT_AGENT_MODEL=mistral-nemo
```

For local development, you'll also need to create a `core/.env` file with your API keys for external services.

### Cloud Deployment with Kubernetes and Terraform

For production deployment to AWS, the entire process can be handled with a single script:

```bash
# Deploy everything (infrastructure, build, push to ECR, and deploy to Kubernetes)
./k8s/deploy.sh --terraform --build --push-to-ecr --deploy

# Deploy without provisioning infrastructure (if already created with Terraform)
./k8s/deploy.sh --build --push-to-ecr --deploy

# To delete everything (Kubernetes resources and Terraform infrastructure)
./k8s/deploy.sh --delete
```

### Available Options

The deploy.sh script supports the following options:

- `--terraform`: Run Terraform init, plan, and apply to provision infrastructure
- `--build`: Build Docker images for Django and API components
- `--push-to-ecr`: Push Docker images to Amazon ECR
- `--deploy`: Deploy the application to Kubernetes
- `--delete`: Delete Kubernetes resources and destroy Terraform infrastructure

### Behind the Scenes

The deployment process involves several steps:

1. **Infrastructure Provisioning with Terraform**:
   - Creates an EKS cluster
   - Sets up ECR repositories
   - Provisions an EC2 GPU instance for Ollama
   - Configures networking and security

2. **Docker Image Building and Publishing**:
   - Builds Docker images for Django and API components
   - Pushes images to ECR repositories

3. **Kubernetes Deployment**:
   - Creates the necessary namespace
   - Deploys ConfigMaps and Secrets
   - Sets up Storage Classes and Persistent Volumes
   - Deploys MySQL, Django, and API services
   - Configures Ollama integration

## Configuration

### Terraform Configuration

All Terraform configuration is done through variables defined in `terraform/variables.tf`. You can set these variables in a `terraform.tfvars` file:

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

### Kubernetes Secrets Configuration

The application requires various secrets and API keys to function properly. These are stored in `k8s/base/secrets/app-secrets.yaml`.

**Important: Do not commit the secrets file to GitHub!**

1. Create your own `app-secrets.yaml` file based on the provided template:

```bash
# Copy the template file to create your own secrets file
cp k8s/base/secrets/app-secrets.template.yaml k8s/base/secrets/app-secrets.yaml
```

2. Edit the `app-secrets.yaml` file to replace the placeholder values with your actual credentials:

   - Database passwords can be set to values of your choice
   - API keys need to be obtained from the respective services:
     - [Wolfram Alpha](https://developer.wolframalpha.com/)
     - [Tavily](https://tavily.com/)
     - [LangChain](https://langchain.com/)
     - [OpenAI](https://platform.openai.com/)
   - AWS credentials should be from an IAM user with appropriate permissions

## SSH Key Pair Configuration

To SSH into the EC2 instance running Ollama, you need to create and specify an SSH key pair:

1. **Specify the key name in your `terraform.tfvars` file**:
   ```hcl
   ssh_key_name = "ollama-key"
   ```

The key is automatically created for you and saved under the terraform directory.

## Accessing the Application

After deployment, the `deploy.sh` script will automatically display the URLs for accessing your application:

```
============================================================
                   ACCESS INFORMATION                       
============================================================
Your application is now accessible at the following URLs:

Django Frontend: http://<DJANGO-HOSTNAME>:8000
API Endpoint: http://<API-HOSTNAME>:8001
API Documentation: http://<API-HOSTNAME>:8001/docs
============================================================
```

It may take a few minutes for the Load Balancers to be provisioned and for DNS to propagate. If you can't access the URLs immediately, wait a few minutes and try again.

## Ollama Integration

The application uses an Ollama instance running on an EC2 instance for LLM inference. The connection to the Ollama instance is managed through a Kubernetes ExternalName service, which allows the application to connect to the Ollama instance using the service name `ollama`.

During deployment, the `deploy.sh` script:
1. Gets the private IP address of the EC2 instance running Ollama
2. Updates the Ollama service configuration with this IP address
3. Configures the application to connect to the Ollama service using the service name `ollama:11434`

This approach ensures that the application can communicate with the Ollama instance even if the IP address changes.

## Cleanup

To remove all resources:

```bash
# This will delete Kubernetes resources, ECR repositories, and all infrastructure
./k8s/deploy.sh --delete
```

**Note**: Running the delete command will remove all infrastructure created by Terraform, including the EKS cluster and ECR repositories. If you want to preserve your Docker images, you should back them up before running this command.

## Troubleshooting

If you encounter issues:

```bash
# Check pod status
kubectl get pods -n newsagent

# View logs for a specific pod
kubectl logs <pod-name> -n newsagent

# Check all resources in the namespace
kubectl get all -n newsagent
```

For Terraform-related issues:

```bash
# Check Terraform state
cd terraform
terraform state list

# Get details about a specific resource
terraform state show <resource_name>
