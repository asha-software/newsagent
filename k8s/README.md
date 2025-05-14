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

## Deploying the Application

### Step 1: Create Infrastructure with Terraform

Before deploying the application, you need to create the necessary infrastructure using Terraform:

```bash
cd terraform
terraform init
terraform apply (optional --auto-approve)
```

This will create:
- EKS cluster
- ECR repositories for Docker images
- EC2 instance for Ollama

### Step 2: Configure Secrets

The application requires various secrets and API keys to function properly. You need to configure the secrets in `k8s/base/secrets/app-secrets.yaml`.

```bash
# Copy the template file to create your own secrets file
cp k8s/base/secrets/app-secrets.template.yaml k8s/base/secrets/app-secrets.yaml
```

Edit the `app-secrets.yaml` file to replace the placeholder values with your actual credentials:
- Database credentials can be set to values of your choice
- API keys need to be obtained from the respective services:
  - [Wolfram Alpha](https://developer.wolframalpha.com/)
  - [Tavily](https://tavily.com/)
  - [LangChain](https://langchain.com/)
  - [OpenAI](https://platform.openai.com/)
- AWS credentials should be from an IAM user with appropriate permissions
- LLM model settings (add these to the file):
  ```yaml
  CLAIM_DECOMPOSER_MODEL: "mistral-nemo"
  RESEARCH_AGENT_MODEL: "mistral-nemo"
  REASONING_AGENT_MODEL: "mistral-nemo"
  VERDICT_AGENT_MODEL: "mistral-nemo"
  ```

**Important**: The repository's `.gitignore` file has been configured to exclude `k8s/base/secrets/app-secrets.yaml` to prevent accidentally committing your secrets to GitHub.

### Step 3: Deploy the Application

The `deploy.sh` script handles all deployment steps for you. The correct order for deployment is:

```bash
# Step 1: Run Terraform first (as described above)

# Step 2: Build the necessary Docker images (Django and API)
./k8s/deploy.sh --build

# Step 3: Push images to ECR (uses repositories created by Terraform)
./k8s/deploy.sh --push-to-ecr

# Step 4: Deploy to Kubernetes
./k8s/deploy.sh --deploy
```

Alternatively, you can combine steps 2-4:
```bash
./k8s/deploy.sh --build --push-to-ecr --deploy
```

**Important Note**: Do not use `--terraform` with `--push-to-ecr` in the same command, as this can cause conflicts with ECR repository creation. The `--push-to-ecr` flag attempts to create ECR repositories if they don't exist, but Terraform also creates these repositories. Always run Terraform separately first, then proceed with the other steps.

The deployment process will:
1. Build the required Docker images
2. Push the images to ECR
3. Create the namespace
4. Deploy all resources in the correct order
5. Wait for the database to be ready before deploying dependent services
6. Install and configure Nvidia drivers, and Ollama on the EC2 instance

Now feel free to get yourself a coffee. This will take about 10 minutes to fully deploy.

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
```

### Common Issues and Solutions

1. **ECR Repository Already Exists Error**:
   - This occurs when using `--terraform` and `--push-to-ecr` together
   - Solution: Run Terraform first, then use `--push-to-ecr` separately

2. **Secret Configuration Issues**:
   - Ensure `app-secrets.yaml` is properly configured with all required values
   - Check that AWS credentials and API keys are valid

3. **Ollama Connection Issues**:
   - Verify the Ollama EC2 instance is running: `aws ec2 describe-instances --filters "Name=tag:Name,Values=ollama-gpu-instance" "Name=instance-state-name,Values=running"`
   - Check that port 11434 is open in the security group
   - SSH into the instance to verify Ollama is running: `ssh -i terraform/ollama-key.pem ubuntu@<OLLAMA_PUBLIC_IP>`
