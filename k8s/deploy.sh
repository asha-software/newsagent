#!/bin/bash

# Script to build and deploy the NewsAgent application to Kubernetes

set -e

# Function to push Docker images with retry
push_with_retry() {
  local image=$1
  local max_attempts=3
  local attempt=1
  
  while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt of $max_attempts: Pushing $image"
    if docker push "$image"; then
      echo "Successfully pushed $image"
      return 0
    else
      echo "Push failed, retrying in 10 seconds..."
      sleep 10
      attempt=$((attempt+1))
    fi
  done
  
  echo "Failed to push $image after $max_attempts attempts"
  return 1
}

# Default values
BUILD_IMAGES=false
DEPLOY=false
DELETE=false
PUSH_TO_ECR=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --build)
      BUILD_IMAGES=true
      shift
      ;;
    --deploy)
      DEPLOY=true
      shift
      ;;
    --delete)
      DELETE=true
      shift
      ;;
    --push-to-ecr)
      PUSH_TO_ECR=true
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --build         Build Docker images"
      echo "  --push-to-ecr   Push Docker images to Amazon ECR"
      echo "  --deploy        Deploy to Kubernetes"
      echo "  --delete        Delete from Kubernetes"
      echo "  --help          Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Set the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Build Docker images if requested
if [ "$BUILD_IMAGES" = true ]; then
  echo "Building Docker images..."
  
  # Remove any existing images to ensure clean builds
  echo "Removing any existing images..."
  docker rmi -f newsagent-django:latest 2>/dev/null || true
  docker rmi -f newsagent-api:latest 2>/dev/null || true
  docker rmi -f "${ECR_REGISTRY}/newsagent-django:latest" 2>/dev/null || true
  docker rmi -f "${ECR_REGISTRY}/newsagent-api:latest" 2>/dev/null || true
  
  # Create and use a new builder that supports multi-architecture builds
  echo "Setting up Docker buildx for multi-architecture builds..."
  docker buildx rm newsagent-builder 2>/dev/null || true
  docker buildx create --name newsagent-builder --use
  docker buildx inspect --bootstrap
  
  echo "Building Django image for x86_64 architecture..."
  DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build -t newsagent-django:latest -f django/Dockerfile django/
  
  echo "Building API image for x86_64 architecture..."
  DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build -t newsagent-api:latest -f core/Dockerfile .
  
  echo "Docker images built successfully."
  echo "Note: MySQL uses the official mysql:8.0 image from Docker Hub, so no build is needed."
fi

# Push Docker images to ECR if requested
if [ "$PUSH_TO_ECR" = true ]; then
  echo "Pushing Docker images to Amazon ECR..."
  
  # Create ECR repositories if they don't exist
  echo "Creating ECR repositories if they don't exist..."
  aws ecr describe-repositories --repository-names newsagent-api >/dev/null 2>&1 || aws ecr create-repository --no-cli-pager --repository-name newsagent-api
  aws ecr describe-repositories --repository-names newsagent-django >/dev/null 2>&1 || aws ecr create-repository --no-cli-pager --repository-name newsagent-django
  
  # Login to ECR
  echo "Logging in to Amazon ECR..."
  aws ecr get-login-password | docker login --username AWS --password-stdin "${ECR_REGISTRY}"
  
  # Tag and push images
  echo "Tagging and pushing newsagent-api image..."
  docker tag newsagent-api:latest "${ECR_REGISTRY}/newsagent-api:latest"
  push_with_retry "${ECR_REGISTRY}/newsagent-api:latest"
  
  echo "Tagging and pushing newsagent-django image..."
  docker tag newsagent-django:latest "${ECR_REGISTRY}/newsagent-django:latest"
  push_with_retry "${ECR_REGISTRY}/newsagent-django:latest"
  
  echo "Docker images pushed to ECR successfully."
  
  # Update deployment files to use ECR images
  echo "Updating deployment files to use ECR images..."
  # Update main container and init container in API deployment
  sed -i.bak "s|image: newsagent-api:latest|image: ${ECR_REGISTRY}/newsagent-api:latest|g" k8s/base/deployments/api.yaml
  
  # Update Django deployment
  sed -i.bak "s|image: newsagent-django:latest|image: ${ECR_REGISTRY}/newsagent-django:latest|g" k8s/base/deployments/django.yaml
  
  # Clean up backup files (if any exist)
  find k8s/base/deployments/ -name "*.bak" -type f -delete 2>/dev/null || true
fi

# Get Ollama instance information
update_ollama_config() {
  echo "Getting Ollama instance information..."
  
  # Get the instance ID with the tag Name=ollama-gpu-instance
  OLLAMA_INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=ollama-gpu-instance" --query "Reservations[0].Instances[0].InstanceId" --output text)
  
  if [ -z "$OLLAMA_INSTANCE_ID" ] || [ "$OLLAMA_INSTANCE_ID" == "None" ]; then
    echo "Error: Could not find Ollama instance with tag Name=ollama-gpu-instance"
    exit 1
  fi
  
  # Get the private IP of the Ollama instance
  OLLAMA_PRIVATE_IP=$(aws ec2 describe-instances --instance-ids "$OLLAMA_INSTANCE_ID" --query "Reservations[0].Instances[0].PrivateIpAddress" --output text)
  
  if [ -z "$OLLAMA_PRIVATE_IP" ] || [ "$OLLAMA_PRIVATE_IP" == "None" ]; then
    echo "Error: Could not get private IP of Ollama instance"
    exit 1
  fi
  
  echo "Found Ollama instance with ID $OLLAMA_INSTANCE_ID and private IP $OLLAMA_PRIVATE_IP"
  
  # Update the ConfigMap with the Ollama instance private IP
  echo "Updating ConfigMap with Ollama instance private IP..."
  sed -i.bak "s|OLLAMA_BASE_URL: \"http://.*:11434\"|OLLAMA_BASE_URL: \"http://${OLLAMA_PRIVATE_IP}:11434\"|g" k8s/base/configmaps/app-config.yaml
  
  # Clean up backup files (if any exist)
  find k8s/base/configmaps/ -name "*.bak" -type f -delete 2>/dev/null || true
  
  echo "ConfigMap updated successfully."
}

# Deploy to Kubernetes if requested
if [ "$DEPLOY" = true ]; then
  echo "Deploying to Kubernetes..."
  
  # Update Ollama configuration
  update_ollama_config
  
  # Create namespace first
  kubectl apply -f k8s/base/namespace.yaml
  
  # Deploy all resources in the correct order
  echo "Deploying ConfigMaps and Secrets..."
  kubectl apply -f k8s/base/configmaps/
  kubectl apply -f k8s/base/secrets/
  
  echo "Deploying Storage Class and Persistent Volumes..."
  kubectl apply -f k8s/base/storage-class.yaml
  kubectl apply -f k8s/base/volumes/
  
  echo "Deploying MySQL Database..."
  kubectl apply -f k8s/base/deployments/mysql.yaml
  kubectl apply -f k8s/base/services/mysql.yaml
  
  echo "Waiting for MySQL to be ready..."
  kubectl wait --for=condition=available --timeout=300s deployment/mysql -n newsagent
  
  echo "Deploying Django and API applications..."
  kubectl apply -f k8s/base/deployments/django.yaml
  kubectl apply -f k8s/base/deployments/api.yaml
  kubectl apply -f k8s/base/services/django.yaml
  kubectl apply -f k8s/base/services/api.yaml
  
  echo "Deploying Ingress..."
  kubectl apply -f k8s/base/ingress.yaml
  
  echo "Deployment completed successfully."
  
  # Display resources
  echo "Resources in namespace 'newsagent':"
  kubectl get all -n newsagent
fi

# Delete from Kubernetes if requested
if [ "$DELETE" = true ]; then
  echo "Deleting from Kubernetes..."
  
  # Delete namespace first (this will delete all resources in the namespace)
  echo "Deleting namespace (if it exists)..."
  kubectl delete namespace newsagent --ignore-not-found=true
  
  # Delete storage class (which is not namespace-scoped)
  echo "Deleting storage class (if it exists)..."
  kubectl delete -f k8s/base/storage-class.yaml --ignore-not-found=true
  
  # Delete ECR images if they exist
  echo "Checking for ECR repositories..."
  
  # Function to delete ECR repository and its images
  delete_ecr_repository() {
    local repo_name=$1
    
    # Check if repository exists
    if aws ecr describe-repositories --no-cli-pager --repository-names "$repo_name" >/dev/null 2>&1; then
      echo "Deleting images from $repo_name repository..."
      
      # Get image digests
      IMAGE_DIGESTS=$(aws ecr list-images --no-cli-pager --repository-name "$repo_name" --query 'imageIds[*].imageDigest' --output text)
      
      # Delete images if any exist
      if [ -n "$IMAGE_DIGESTS" ]; then
        for DIGEST in $IMAGE_DIGESTS; do
          aws ecr batch-delete-image --no-cli-pager --repository-name "$repo_name" --image-ids imageDigest=$DIGEST
        done
        echo "Images deleted from $repo_name repository."
      else
        echo "No images found in $repo_name repository."
      fi
      
      # Delete the repository itself
      echo "Deleting $repo_name repository..."
      aws ecr delete-repository --no-cli-pager --repository-name "$repo_name" --force
      echo "$repo_name repository deleted."
    else
      echo "$repo_name repository does not exist."
    fi
  }
  
  # Delete ECR repositories and their images
  delete_ecr_repository "newsagent-api"
  delete_ecr_repository "newsagent-django"
  
  echo "Deletion completed successfully."
fi

echo "Done."
