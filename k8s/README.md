# NewsAgent Kubernetes Deployment

This directory contains Kubernetes manifests and deployment scripts for the NewsAgent application on AWS EKS with GPU support.

## Architecture

The NewsAgent application consists of the following components:

1. **API Service**: Core API endpoint for the application
2. **Django Application**: Web interface for user interaction
3. **Database**: MySQL database for storing application data
4. **Ollama**: Running the mistral-nemo model on GPU-enabled nodes

The infrastructure is deployed on AWS EKS with g4dn.xlarge instances that provide GPU capabilities for the Ollama service.

## Prerequisites

Before deploying, ensure you have the following tools installed:

- AWS CLI
- kubectl
- Terraform
- Docker
- [skopeo](https://github.com/containers/skopeo/blob/main/install.md) - For reliable image pushing with retry capability

You also need to have AWS credentials configured with appropriate permissions to create EKS clusters, ECR repositories, and other AWS resources.

## Deployment Process

The deployment process is fully automated using the `deploy.sh` script, which performs the following steps:

1. Checks prerequisites
2. Verifies AWS authentication
3. Creates infrastructure using Terraform
4. Builds and pushes Docker images to ECR
5. Deploys Kubernetes resources
6. Configures NVIDIA drivers for GPU support
7. Provides deployment information

### Quick Start

To deploy the application:

```bash
# Make the script executable (if not already)
chmod +x deploy.sh

# Run the deployment script
./deploy.sh
```

## Kubernetes Resources

The deployment creates the following Kubernetes resources:

- **Namespace**: `newsagent`
- **Secrets**: Database credentials, API keys, and AWS credentials
- **ConfigMap**: Configuration for all services
- **Deployments**: For API, Django, Database, and Ollama services
- **Services**: For internal communication between components
- **Ingress**: For external access to the API and Django application
- **NVIDIA Device Plugin**: For GPU support
- **Network Policies**: For secure communication between services
- **Service Account**: For pod authentication and authorization to the Kubernetes API

## Service Account and RBAC

The deployment includes a Kubernetes service account (`newsagent-service-account`) that provides the necessary permissions for pods to interact with the Kubernetes API. This service account is defined in `service-account.yaml` and includes:

- A ServiceAccount resource
- A Role with specific permissions (get, list, watch) for pods, services, configmaps, secrets, and deployments
- A RoleBinding that connects the ServiceAccount to the Role

All pods in the deployment use this service account, which allows them to:
- Discover other services in the cluster
- Access configuration and secrets
- Monitor the status of other pods and deployments

You can customize the permissions by modifying the Role in `service-account.yaml` if your application requires additional access to Kubernetes resources.

## Service Communication

The services communicate with each other using Kubernetes DNS service discovery:

- **API Service** communicates with:
  - Database using `newsagent-db:3306`
  - Ollama using `newsagent-ollama:11434`

- **Django Application** communicates with:
  - Database using `newsagent-db:3306`
  - API Service using `newsagent-api:8000`
  - Ollama using `newsagent-ollama:11434`

- **Ollama Service** is configured to:
  - Accept connections from API and Django services
  - Use GPU resources for model inference

The environment variables in each deployment are configured to use these service URLs, ensuring proper communication in the Kubernetes environment.

## GPU Support

The deployment includes the NVIDIA device plugin for Kubernetes, which enables GPU support for the Ollama service. The Ollama pod is scheduled on nodes with GPU capabilities and has access to the GPU resources.

## Customization

### Secrets

The repository includes a `secrets-template.yaml` file that contains the structure of required secrets with placeholder values. To set up your environment:

1. Copy `secrets-template.yaml` to `secrets.yaml`:
   ```bash
   cp k8s/secrets-template.yaml k8s/secrets.yaml
   ```

2. Edit `secrets.yaml` to replace the placeholder values with your actual credentials:
   ```bash
   # Example for database credentials
   DB_PASSWORD: "your_actual_password"
   
   # Example for API keys
   OPENAI_API_KEY: "sk-your_actual_openai_key"
   ```

3. The actual `secrets.yaml` file is excluded from version control via `.gitignore` to prevent accidental exposure of sensitive information.

In a production environment, you should use a secrets management solution like AWS Secrets Manager, HashiCorp Vault, or Kubernetes Secrets encrypted with sealed-secrets or external-secrets.

### Configuration

The `configmap.yaml` file contains configuration for all services. You can modify this file to customize the application behavior.

## Troubleshooting

If you encounter issues during deployment:

1. Check the logs of the failing pods:
   ```bash
   kubectl logs -n newsagent <pod-name>
   ```

2. Verify that the NVIDIA device plugin is running:
   ```bash
   kubectl get pods -n kube-system | grep nvidia
   ```

3. Check if GPU resources are available:
   ```bash
   kubectl describe nodes | grep nvidia.com/gpu
   ```

## Reliable Image Pushing with Skopeo

The deployment script uses `skopeo` instead of standard Docker push commands to upload images to ECR. This provides several advantages:

1. **Advanced Authentication**: Uses a custom auth file to avoid ECR authentication issues
2. **Retry Capability**: Automatically retries failed pushes with exponential backoff
3. **Chunked Transfers**: Handles large images better by pushing in chunks
4. **Network Resilience**: Better handling of network interruptions and timeouts
5. **Progress Tracking**: Provides better visibility into the push process

The script includes a custom `push_image_with_retry` function that:
- Creates a temporary auth file with ECR credentials
- Uses the `--all` flag to force pushing all layers (avoiding reuse issues)
- Disables TLS verification for the destination to avoid certificate issues
- Attempts to push images up to 5 times
- Implements exponential backoff between retries
- Refreshes ECR credentials before each retry
- Provides clear status messages during the process

This approach significantly improves reliability when pushing large images or when working with unstable network connections, ensuring that temporary network issues don't cause the entire deployment to fail.

## Re-running the Deployment

If you run `deploy.sh` again after a successful deployment:

1. **Terraform Infrastructure**: 
   - Terraform uses state tracking to determine what resources already exist
   - It will compare the desired state (in your .tf files) with the current state
   - Only missing resources will be created, existing ones will be left unchanged
   - If you've made changes to the Terraform files, only the affected resources will be updated

2. **Docker Images**:
   - Images will be rebuilt and pushed to ECR with the same tags
   - This will overwrite the previous images in ECR
   - If no changes were made to the source code, the build will be fast due to Docker layer caching

3. **Kubernetes Resources**:
   - The `kubectl apply` commands will update existing resources rather than recreating them
   - Resources that haven't changed won't be modified
   - Resources with changes will be updated in-place when possible
   - Some updates might trigger a rolling restart of pods

This idempotent behavior means you can safely run the script multiple times without duplicating resources. It's also useful for applying changes or recovering from partial deployments.

## Cleanup

To delete all resources created by this deployment:

1. Delete Kubernetes resources:
   ```bash
   kubectl delete namespace newsagent
   kubectl delete -f nvidia-device-plugin.yaml
   ```

2. Destroy Terraform infrastructure:
   ```bash
   cd ../terraform
   terraform destroy
   ```
