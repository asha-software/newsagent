# Kubernetes Deployment for NewsAgent

This directory contains Kubernetes manifests for deploying the NewsAgent application, which consists of:

1. MySQL Database (using the official mysql:8.0 image)
2. Django Web Application
3. FastAPI Application (API)

The application uses Amazon ECR (Elastic Container Registry) to store Docker images for the Django and API components. These ECR repositories are created and managed by Terraform.

## Prerequisites

Before deploying, ensure you have:

1. A Kubernetes cluster (EKS) on AWS
2. `kubectl` installed and configured
3. AWS CLI installed and configured

## Connecting to AWS EKS

1. Configure AWS CLI with your credentials:
   ```bash
   aws configure
   ```

2. Update your kubeconfig to connect to your EKS cluster:
   ```bash
   aws eks update-kubeconfig --region <your-region> --name <your-cluster-name>
   ```

3. Verify the connection:
   ```bash
   kubectl get nodes
   ```

## Deploying the Application

### Step 1: Create Infrastructure with Terraform

Before deploying the application, you need to create the necessary infrastructure using Terraform:

```bash
cd terraform
terraform init
terraform apply
```

This will create:
- EKS cluster
- ECR repositories for Docker images
- EC2 instance for Ollama

### Step 2: Configure Secrets

The application requires various secrets and API keys to function properly. These are stored in `k8s/base/secrets/app-secrets.yaml`.

**Important: Do not commit the secrets file to GitHub!**

1. Create your own `app-secrets.yaml` file based on the template below:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: newsagent
type: Opaque
stringData:
  # Database credentials
  DB_PASSWORD: "your-db-password"
  MYSQL_ROOT_PASSWORD: "your-mysql-root-password"
  MYSQL_PASSWORD: "your-mysql-password"
  
  # API keys
  WOLFRAM_APP_ID: "your-wolfram-app-id"
  TAVILY_API_KEY: "your-tavily-api-key"
  LANGCHAIN_API_KEY: "your-langchain-api-key"
  OPENAI_API_KEY: "your-openai-api-key"
  
  # AWS credentials
  AWS_ACCESS_KEY_ID: "your-aws-access-key-id"
  AWS_SECRET_ACCESS_KEY: "your-aws-secret-access-key"
  AWS_REGION: "your-aws-region"
```

2. Replace all placeholder values with your actual credentials:
   - Database passwords can be set to values of your choice
   - API keys need to be obtained from the respective services:
     - [Wolfram Alpha](https://developer.wolframalpha.com/)
     - [Tavily](https://tavily.com/)
     - [LangChain](https://langchain.com/)
     - [OpenAI](https://platform.openai.com/)
   - AWS credentials should be from an IAM user with appropriate permissions

3. Consider adding `k8s/base/secrets/app-secrets.yaml` to your `.gitignore` file to prevent accidentally committing it.

### Step 3: Deploy the Application

The `deploy.sh` script handles all deployment steps for you:

```bash
# Build the necessary Docker images (Django and API)
./k8s/deploy.sh --build

# Push images to ECR
./k8s/deploy.sh --push-to-ecr

# Deploy to Kubernetes
./k8s/deploy.sh --deploy
```

You can also combine these steps:
```bash
./k8s/deploy.sh --build --push-to-ecr --deploy
```

The script will:
1. Build the required Docker images
2. Push the images to ECR (if --push-to-ecr is specified)
3. Create the namespace
4. Deploy all resources in the correct order
5. Wait for the database to be ready before deploying dependent services

**Note**: The ECR repositories must exist before pushing images. They are created by Terraform as part of the infrastructure setup.

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

The script will wait for the load balancers to be provisioned and display these URLs automatically. If for some reason the URLs are not displayed, you can manually check them with:

```bash
# Get the external hostnames for the Django and API services
kubectl get services -n newsagent
```

Look for the `EXTERNAL-IP` column in the output. You'll see external hostnames for both the Django and API services:

- Django frontend: `http://<DJANGO-EXTERNAL-IP>:8000`
- API endpoint: `http://<API-EXTERNAL-IP>:8001`
- API documentation: `http://<API-EXTERNAL-IP>:8001/docs`

It may take a few minutes for the Load Balancers to be provisioned and for DNS to propagate. If you can't access the URLs immediately, wait a few minutes and try again.

For class demonstrations, you can share these URLs with your audience to access the application.

### Quick URL Check

If you need to quickly check the URLs after deployment, you can use the provided script:

```bash
./k8s/get_urls.sh
```

This script will display the current URLs for the Django frontend and API endpoints, as well as the current status of all services.

## Cleanup

To remove all Kubernetes resources and ECR images:

```bash
./k8s/deploy.sh --delete
```

To remove all infrastructure created by Terraform (including EKS cluster and ECR repositories):

```bash
cd terraform
terraform destroy
```

**Note**: Running `terraform destroy` will delete the ECR repositories and all images stored in them. If you want to preserve your Docker images, you should back them up before running this command.

## Ollama Integration

The application uses an Ollama instance running on an EC2 instance for LLM inference. The connection to the Ollama instance is managed through a Kubernetes ExternalName service, which allows the application to connect to the Ollama instance using the service name `ollama`.

During deployment, the `deploy.sh` script:
1. Gets the private IP address of the EC2 instance running Ollama
2. Updates the Ollama service configuration with this IP address
3. Configures the application to connect to the Ollama service using the service name `ollama:11434`

This approach ensures that the application can communicate with the Ollama instance even if the IP address changes.

## Troubleshooting

If you encounter issues:

```bash
# Check pod status
kubectl get pods -n newsagent

# View logs for a specific pod
kubectl logs <pod-name> -n newsagent

# Check all resources in the namespace
kubectl get all -n newsagent

# Test connectivity to the Ollama instance
kubectl run curl-test --image=curlimages/curl --rm -it -- curl http://ollama:11434/api/tags
