#!/bin/bash
set -e

# Disable AWS CLI pagination to prevent interactive pager
export AWS_PAGER=""

# Display help message
show_help() {
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Deploy the NewsAgent application to Kubernetes."
  echo ""
  echo "Options:"
  echo "  --delete    Delete all Kubernetes resources before deploying"
  echo "  --help      Display this help message and exit"
  echo ""
  echo "Examples:"
  echo "  $0                  # Deploy the application"
  echo "  $0 --delete         # Delete existing resources and exit"
  echo "  $0 --help           # Show this help message"
}

# Parse command line arguments
DELETE_MODE=false
for arg in "$@"; do
  case $arg in
    --delete)
      DELETE_MODE=true
      shift
      ;;
    --help)
      show_help
      exit 0
      ;;
    *)
      # Unknown option
      echo "Unknown option: $arg"
      show_help
      exit 1
      ;;
  esac
done

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print section header
print_section() {
  echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

# Print info message
print_info() {
  echo -e "${YELLOW}$1${NC}"
}

# Print error message
print_error() {
  echo -e "${RED}ERROR: $1${NC}"
  exit 1
}

# Check if required tools are installed
check_prerequisites() {
  print_section "Checking prerequisites"
  
  # Check AWS CLI
  if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
  fi
  
  # Check kubectl
  if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install it first."
  fi
  
  # Check Terraform
  if ! command -v terraform &> /dev/null; then
    print_error "Terraform is not installed. Please install it first."
  fi
  
  # Check Docker
  if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install it first."
  fi
  
  # Check skopeo
  if ! command -v skopeo &> /dev/null; then
    print_error "skopeo is not installed. Please install it first (https://github.com/containers/skopeo/blob/main/install.md)."
  fi
  
  print_info "All prerequisites are installed."
}

# Check AWS authentication
check_aws_auth() {
  print_section "Checking AWS authentication"
  
  if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS authentication failed. Please configure your AWS credentials."
  fi
  
  print_info "AWS authentication successful."
  
  # Get AWS account ID
  AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  AWS_REGION=$(aws configure get region)
  
  if [ -z "$AWS_REGION" ]; then
    AWS_REGION="us-west-2"
    print_info "AWS region not configured, using default: $AWS_REGION"
  fi
  
  print_info "AWS Account ID: $AWS_ACCOUNT_ID"
  print_info "AWS Region: $AWS_REGION"
  
  # Export variables for later use
  export AWS_ACCOUNT_ID
  export AWS_REGION
}

# Create infrastructure using Terraform
create_infrastructure() {
  print_section "Creating infrastructure with Terraform"
  
  cd ../terraform
  
  print_info "Initializing Terraform..."
  terraform init
  
  print_info "Planning Terraform deployment..."
  terraform plan -out=tfplan
  
  print_info "Applying Terraform plan..."
  terraform apply -auto-approve tfplan
  
  # Get EKS cluster name
  CLUSTER_NAME=$(terraform output -raw cluster_name)
  
  # Configure kubectl to use the EKS cluster
  print_info "Configuring kubectl to use the EKS cluster..."
  aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME
  
  print_info "Infrastructure created successfully."
  
  cd ../k8s
}

# Function to check if image exists in ECR with the same digest
image_needs_push() {
  local source_image=$1
  local repo_name=$2
  
  # Get local image digest
  local local_digest=$(docker inspect --format='{{index .RepoDigests 0}}' $source_image 2>/dev/null || echo "")
  
  if [ -z "$local_digest" ]; then
    # If we can't get the digest, assume we need to push
    return 0
  fi
  
  # Extract just the sha256 part
  local_digest=$(echo $local_digest | cut -d '@' -f 2)
  
  # Try to get the remote image digest
  local remote_digest=""
  if aws ecr describe-images --repository-name $repo_name --region $AWS_REGION --query 'imageDetails[?contains(imageTags, `latest`)].imageDigest' --output text 2>/dev/null; then
    remote_digest=$(aws ecr describe-images --repository-name $repo_name --region $AWS_REGION --query 'imageDetails[?contains(imageTags, `latest`)].imageDigest' --output text)
  fi
  
  if [ -z "$remote_digest" ]; then
    # If remote image doesn't exist, we need to push
    return 0
  fi
  
  # Compare digests
  if [ "$local_digest" = "$remote_digest" ]; then
    # Digests match, no need to push
    return 1
  else
    # Digests don't match, need to push
    return 0
  fi
}

# Function to push image with skopeo and retry logic
push_image_with_retry() {
  local source_image=$1
  local dest_image=$2
  local repo_name=$3
  local max_retries=5
  local retry_count=0
  local success=false

  # Check if we need to push the image
  if ! image_needs_push "$source_image" "$repo_name"; then
    print_info "Image $source_image already exists in ECR with the same digest. Skipping push."
    return 0
  fi
  
  print_info "Pushing image $source_image to $dest_image..."
  
  # Get ECR password for skopeo
  ECR_PASSWORD=$(aws ecr get-login-password --region $AWS_REGION)
  
  # Create a temporary auth.json file for skopeo
  TEMP_AUTH_FILE=$(mktemp)
  cat > $TEMP_AUTH_FILE << EOF
{
  "auths": {
    "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com": {
      "auth": "$(echo -n "AWS:$ECR_PASSWORD" | base64)"
    }
  }
}
EOF
  
  while [ $retry_count -lt $max_retries ] && [ "$success" = false ]; do
    if [ $retry_count -gt 0 ]; then
      print_info "Retry attempt $retry_count of $max_retries..."
      sleep $((retry_count * 5)) # Exponential backoff
      
      # Refresh ECR password
      print_info "Refreshing ECR credentials..."
      ECR_PASSWORD=$(aws ecr get-login-password --region $AWS_REGION)
      cat > $TEMP_AUTH_FILE << EOF
{
  "auths": {
    "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com": {
      "auth": "$(echo -n "AWS:$ECR_PASSWORD" | base64)"
    }
  }
}
EOF
    fi
    
    # Use skopeo with the auth file
    if skopeo copy --authfile $TEMP_AUTH_FILE --dest-tls-verify=false --src-no-creds --all docker-daemon:$source_image docker://$dest_image; then
      success=true
      print_info "Successfully pushed $source_image to $dest_image"
    else
      retry_count=$((retry_count + 1))
      if [ $retry_count -eq $max_retries ]; then
        rm -f $TEMP_AUTH_FILE
        print_error "Failed to push $source_image after $max_retries attempts"
      else
        print_info "Push failed, will retry..."
      fi
    fi
  done
  
  # Clean up the temporary auth file
  rm -f $TEMP_AUTH_FILE
}

# Build and push Docker images to ECR
build_and_push_images() {
  print_section "Building and pushing Docker images to ECR"
  
  # Login to ECR
  print_info "Logging in to ECR..."
  aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
  
  # Ensure ECR repositories exist
  for repo in newsagent-api newsagent-django newsagent-db; do
    if ! aws ecr describe-repositories --repository-names $repo --region $AWS_REGION &>/dev/null; then
      print_info "Creating ECR repository: $repo"
      aws ecr create-repository --repository-name $repo --region $AWS_REGION
    fi
  done
  
  # Build and push API image
  print_info "Building API image..."
  # Navigate to the project root directory to ensure proper context for Docker build
  cd ..
  
  print_info "Building multi-architecture image for API (amd64)..."
  docker buildx create --use --name multi-arch-builder || true
  docker buildx build --platform linux/amd64 -t newsagent-api:latest -f core/Dockerfile . --load
  push_image_with_retry "newsagent-api:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/newsagent-api:latest" "newsagent-api"
  
  # Build and push Django image
  print_info "Building Django image..."
  print_info "Building multi-architecture image for Django (amd64)..."
  docker buildx build --platform linux/amd64 -t newsagent-django:latest -f django/Dockerfile . --load
  push_image_with_retry "newsagent-django:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/newsagent-django:latest" "newsagent-django"
  
  # Build and push DB image
  print_info "Building DB image..."
  
  # Check if Dockerfile.mysql exists, if not create it
  if [ ! -f django/Dockerfile.mysql ]; then
    print_info "Dockerfile.mysql not found, creating a default MySQL Dockerfile..."
    cat > django/Dockerfile.mysql << EOF
FROM mysql:8.0

# Copy initialization SQL script
COPY django/sql/init.sql /docker-entrypoint-initdb.d/

# Set environment variables
ENV MYSQL_ROOT_PASSWORD=root
ENV MYSQL_DATABASE=newsagent
ENV MYSQL_USER=newsagent
ENV MYSQL_PASSWORD=newsagent

# Expose MySQL port
EXPOSE 3306

# Set healthcheck
HEALTHCHECK --interval=5s --timeout=5s --retries=3 CMD mysqladmin ping -h localhost -u root -p\${MYSQL_ROOT_PASSWORD}
EOF
  fi
  
  # Ensure sql/init.sql exists
  if [ ! -d django/sql ]; then
    print_info "Creating django/sql directory..."
    mkdir -p django/sql
  fi
  
  if [ ! -f django/sql/init.sql ]; then
    print_info "init.sql not found, creating a default initialization script..."
    cat > django/sql/init.sql << EOF
-- Create database if not exists
CREATE DATABASE IF NOT EXISTS newsagent;
USE newsagent;

-- Create tables if they don't exist yet
-- This is a minimal example, adjust according to your actual schema
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add any other initialization SQL here
EOF
  fi
  
  print_info "Building multi-architecture image for DB (amd64)..."
  docker buildx build --platform linux/amd64 -t newsagent-db:latest -f django/Dockerfile.mysql . --load
  push_image_with_retry "newsagent-db:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/newsagent-db:latest" "newsagent-db"
  
  # Return to k8s directory
  cd k8s
  
  # Skip building and pushing Ollama image since we're using the official image directly
  print_info "Using official Ollama image from Docker Hub instead of building a custom one"
  print_info "This avoids the need to push a large image to ECR"
  
  print_info "All images built and pushed successfully."
}

# Deploy Kubernetes resources
deploy_kubernetes() {
  print_section "Deploying Kubernetes resources"
  
  # Replace variables in Kubernetes manifests
  print_info "Preparing Kubernetes manifests..."
  
  # Create a temporary directory for processed manifests
  mkdir -p temp_manifests
  
  # Process each YAML file
  for file in *.yaml; do
    cat $file | sed "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g" | sed "s/\${AWS_REGION}/$AWS_REGION/g" > temp_manifests/$file
  done
  
  # Create namespace
  print_info "Creating namespace..."
  kubectl apply -f temp_manifests/namespace.yaml
  
  # Apply NVIDIA device plugin
  print_info "Deploying NVIDIA device plugin..."
  kubectl apply -f temp_manifests/nvidia-device-plugin.yaml
  
  # Install AWS EBS CSI driver
  print_info "Installing AWS EBS CSI driver..."
  kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.28"
  
  # Add toleration to EBS CSI controller
  print_info "Adding toleration to EBS CSI controller..."
  kubectl patch deployment ebs-csi-controller -n kube-system -p '{"spec":{"template":{"spec":{"tolerations":[{"key":"nvidia.com/gpu","operator":"Equal","value":"true","effect":"NoSchedule"}]}}}}'
  
  # Add toleration to CoreDNS deployment
  print_info "Adding toleration to CoreDNS deployment..."
  kubectl patch deployment coredns -n kube-system -p '{"spec":{"template":{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/master","effect":"NoSchedule"},{"key":"CriticalAddonsOnly","operator":"Exists"},{"key":"nvidia.com/gpu","operator":"Equal","value":"true","effect":"NoSchedule"}]}}}}'
  
  # Wait for EBS CSI driver to be ready
  print_info "Waiting for EBS CSI driver to be ready..."
  kubectl rollout status deployment/ebs-csi-controller -n kube-system
  
  # Wait for CoreDNS to be ready
  print_info "Waiting for CoreDNS to be ready..."
  kubectl rollout status deployment/coredns -n kube-system
  
  # Apply secrets and configmap
  print_info "Deploying secrets and configmap..."
  kubectl apply -f temp_manifests/secrets.yaml
  kubectl apply -f temp_manifests/configmap.yaml
  
  # Apply network policies
  print_info "Deploying network policies..."
  kubectl apply -f temp_manifests/network-policy.yaml
  
  # Create service account and RBAC resources
  print_info "Creating service account and RBAC resources..."
  kubectl apply -f temp_manifests/service-account.yaml
  print_info "Service account 'newsagent-service-account' created with required permissions"
  
  # Apply database deployment
  print_info "Deploying database..."
  kubectl apply -f temp_manifests/db-deployment.yaml
  
  # Wait for database to be ready
  print_info "Waiting for database to be ready..."
  kubectl rollout status deployment/newsagent-db -n newsagent
  
  # Apply API and Django deployments
  print_info "Deploying API and Django applications..."
  kubectl apply -f temp_manifests/api-deployment.yaml
  kubectl apply -f temp_manifests/django-deployment.yaml
  
  # Apply Ollama deployment
  print_info "Deploying Ollama with GPU support..."
  kubectl apply -f temp_manifests/ollama-deployment.yaml
  
  # Wait for all deployments to be ready
  print_info "Waiting for all deployments to be ready..."
  kubectl rollout status deployment/newsagent-api -n newsagent
  kubectl rollout status deployment/newsagent-django -n newsagent
  kubectl rollout status deployment/newsagent-ollama -n newsagent
  
  # Clean up temporary files
  rm -rf temp_manifests
  
  print_info "All Kubernetes resources deployed successfully."
}

# Get deployment information
get_deployment_info() {
  print_section "Deployment Information"
  
  # Get ingress URLs
  print_info "Getting application URLs..."
  
  # Get ALB hostnames
  DJANGO_INGRESS=$(kubectl get ingress newsagent-django-ingress -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
  API_INGRESS=$(kubectl get ingress newsagent-api-ingress -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
  
  if [ -z "$DJANGO_INGRESS" ] || [ -z "$API_INGRESS" ]; then
    print_info "Ingress hostnames not found. Trying to get service information..."
    
    # Try to get service information
    DJANGO_SERVICE=$(kubectl get svc newsagent-django -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    API_SERVICE=$(kubectl get svc newsagent-api -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    
    if [ -n "$DJANGO_SERVICE" ]; then
      DJANGO_INGRESS=$DJANGO_SERVICE
    fi
    
    if [ -n "$API_SERVICE" ]; then
      API_INGRESS=$API_SERVICE
    fi
  fi
  
  # Get ALB information from AWS CLI if still not found
  if [ -z "$DJANGO_INGRESS" ] || [ -z "$API_INGRESS" ]; then
    print_info "Trying to get ALB information from AWS CLI..."
    
    # Get all load balancers
    LBS=$(aws elbv2 describe-load-balancers --query 'LoadBalancers[*].{DNSName:DNSName,LoadBalancerArn:LoadBalancerArn}' --output json)
    
    # Get all target groups
    TGS=$(aws elbv2 describe-target-groups --query 'TargetGroups[*].{TargetGroupArn:TargetGroupArn,LoadBalancerArns:LoadBalancerArns}' --output json)
    
    # Find target groups associated with our services
    DJANGO_TG=$(kubectl get ingress newsagent-django-ingress -n newsagent -o jsonpath='{.metadata.annotations.alb\.ingress\.kubernetes\.io/target-group-arn}' 2>/dev/null)
    API_TG=$(kubectl get ingress newsagent-api-ingress -n newsagent -o jsonpath='{.metadata.annotations.alb\.ingress\.kubernetes\.io/target-group-arn}' 2>/dev/null)
    
    # If we found target groups, find the associated load balancers
    if [ -n "$DJANGO_TG" ]; then
      DJANGO_LB=$(echo $TGS | jq -r --arg tg "$DJANGO_TG" '.[] | select(.TargetGroupArn==$tg) | .LoadBalancerArns[0]')
      if [ -n "$DJANGO_LB" ]; then
        DJANGO_INGRESS=$(echo $LBS | jq -r --arg lb "$DJANGO_LB" '.[] | select(.LoadBalancerArn==$lb) | .DNSName')
      fi
    fi
    
    if [ -n "$API_TG" ]; then
      API_LB=$(echo $TGS | jq -r --arg tg "$API_TG" '.[] | select(.TargetGroupArn==$tg) | .LoadBalancerArns[0]')
      if [ -n "$API_LB" ]; then
        API_INGRESS=$(echo $LBS | jq -r --arg lb "$API_LB" '.[] | select(.LoadBalancerArn==$lb) | .DNSName')
      fi
    fi
  fi
  
  echo -e "\n${GREEN}Deployment completed successfully!${NC}"
  echo -e "\n${GREEN}Application URLs:${NC}"
  
  if [ -n "$DJANGO_INGRESS" ]; then
    echo -e "${YELLOW}Django Application:${NC} http://$DJANGO_INGRESS:8000"
  else
    echo -e "${YELLOW}Django Application:${NC} URL not found. Run './get_urls.sh' later to check."
  fi
  
  if [ -n "$API_INGRESS" ]; then
    echo -e "${YELLOW}API Endpoint:${NC} http://$API_INGRESS:8000/api"
  else
    echo -e "${YELLOW}API Endpoint:${NC} URL not found. Run './get_urls.sh' later to check."
  fi
  
  # Get pod status
  echo -e "\n${YELLOW}Pod Status:${NC}"
  kubectl get pods -n newsagent
}

# Delete AWS resources that might cause conflicts
delete_aws_resources() {
  print_section "Deleting conflicting AWS resources"
  
  # Get cluster name from variables
  CLUSTER_NAME="newsagent-eks-cluster"  # This should match var.cluster_name in variables.tf
  
  # Delete IAM roles that might cause conflicts
  print_info "Checking and deleting IAM roles..."
  
  # Check if the cluster role exists
  if aws iam get-role --role-name "${CLUSTER_NAME}-cluster-role" 2>/dev/null; then
    print_info "Deleting IAM role: ${CLUSTER_NAME}-cluster-role"
    
    # First detach policies
    for policy in "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy" "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"; do
      print_info "Detaching policy: $policy"
      aws iam detach-role-policy --role-name "${CLUSTER_NAME}-cluster-role" --policy-arn "$policy" || true
    done
    
    # Delete the role
    aws iam delete-role --role-name "${CLUSTER_NAME}-cluster-role" || true
  else
    print_info "IAM role ${CLUSTER_NAME}-cluster-role does not exist. Skipping."
  fi
  
  # Check if the node role exists
  if aws iam get-role --role-name "${CLUSTER_NAME}-node-role" 2>/dev/null; then
    print_info "Deleting IAM role: ${CLUSTER_NAME}-node-role"
    
    # First detach policies
    for policy in "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy" "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy" "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"; do
      print_info "Detaching policy: $policy"
      aws iam detach-role-policy --role-name "${CLUSTER_NAME}-node-role" --policy-arn "$policy" || true
    done
    
    # Delete the role
    aws iam delete-role --role-name "${CLUSTER_NAME}-node-role" || true
  else
    print_info "IAM role ${CLUSTER_NAME}-node-role does not exist. Skipping."
  fi
  
  # Delete ECR repositories that might cause conflicts
  print_info "Checking and deleting ECR repositories..."
  
  for repo in "newsagent-api" "newsagent-django" "newsagent-db" "newsagent-ollama"; do
    if aws ecr describe-repositories --repository-names "$repo" --region $AWS_REGION 2>/dev/null; then
      print_info "Deleting ECR repository: $repo"
      aws ecr delete-repository --repository-name "$repo" --region $AWS_REGION --force || true
    else
      print_info "ECR repository $repo does not exist. Skipping."
    fi
  done
  
  print_info "AWS resource cleanup completed."
}

# Delete all Kubernetes resources
delete_kubernetes_resources() {
  print_section "Deleting Kubernetes resources"
  
  # Check if we can connect to the Kubernetes cluster
  if ! kubectl cluster-info &> /dev/null; then
    print_info "Unable to connect to Kubernetes cluster. Skipping Kubernetes resource deletion."
    return
  fi
  
  # Remove toleration from CoreDNS deployment
  print_info "Removing toleration from CoreDNS deployment..."
  kubectl patch deployment coredns -n kube-system -p '{"spec":{"template":{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/master","effect":"NoSchedule"},{"key":"CriticalAddonsOnly","operator":"Exists"}]}}}}'
  
  # Check if namespace exists
  if kubectl get namespace newsagent &> /dev/null; then
    print_info "Deleting all resources in the newsagent namespace..."
    
    # Delete deployments first to ensure graceful termination
    print_info "Deleting deployments..."
    kubectl delete deployment --all -n newsagent --timeout=60s || true
    
    # Delete services
    print_info "Deleting services..."
    kubectl delete service --all -n newsagent --timeout=30s || true
    
    # Delete ingresses
    print_info "Deleting ingresses..."
    kubectl delete ingress --all -n newsagent --timeout=30s || true
    
    # Delete configmaps
    print_info "Deleting configmaps..."
    kubectl delete configmap --all -n newsagent --timeout=30s || true
    
    # Delete secrets
    print_info "Deleting secrets..."
    kubectl delete secret --all -n newsagent --timeout=30s || true
    
    # Delete PVCs
    print_info "Deleting persistent volume claims..."
    kubectl delete pvc --all -n newsagent --timeout=30s || true
    
    # Delete service accounts
    print_info "Deleting service accounts..."
    kubectl delete serviceaccount --all -n newsagent --timeout=30s || true
    
    # Delete network policies
    print_info "Deleting network policies..."
    kubectl delete networkpolicy --all -n newsagent --timeout=30s || true
    
    # Finally delete the namespace itself
    print_info "Deleting namespace..."
    kubectl delete namespace newsagent --timeout=60s || true
    
    # Wait for namespace to be fully deleted
    print_info "Waiting for namespace to be fully deleted..."
    while kubectl get namespace newsagent &> /dev/null; do
      echo -n "."
      sleep 2
    done
    echo ""
  else
    print_info "Namespace 'newsagent' does not exist. Nothing to delete."
  fi
  
  print_info "All Kubernetes resources deleted successfully."
}

# Main function
main() {
  check_prerequisites
  check_aws_auth
  
  if [ "$DELETE_MODE" = true ]; then
    print_info "Running in DELETE mode"
    delete_kubernetes_resources
    delete_aws_resources
    print_info "Delete operation completed. Run the script without --delete to redeploy."
    exit 0
  fi
  
  create_infrastructure
  build_and_push_images
  deploy_kubernetes
  get_deployment_info
}

# Run the main function
main
