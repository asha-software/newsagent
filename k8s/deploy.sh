#!/bin/bash

# Script to build and deploy the NewsAgent application to Kubernetes

set -e

# Function to ensure skopeo is installed
ensure_skopeo_installed() {
  if ! command -v skopeo &> /dev/null; then
    echo "Skopeo not found. Installing skopeo..."
    
    # Check the OS and install accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
      # For Ubuntu/Debian
      if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y skopeo
      # For RHEL/CentOS/Fedora
      elif command -v yum &> /dev/null; then
        sudo yum install -y skopeo
      elif command -v dnf &> /dev/null; then
        sudo dnf install -y skopeo
      else
        echo "Unsupported Linux distribution. Please install skopeo manually."
        exit 1
      fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
      # For macOS
      if command -v brew &> /dev/null; then
        brew install skopeo
      else
        echo "Homebrew not found. Please install Homebrew first, then skopeo."
        exit 1
      fi
    else
      echo "Unsupported operating system. Please install skopeo manually."
      exit 1
    fi
    
    echo "Skopeo installed successfully."
  else
    echo "Skopeo is already installed."
  fi
}

# Function to push Docker images with skopeo
push_with_skopeo() {
  local source_image=$1
  local dest_image=$2
  local max_attempts=10
  local attempt=1
  
  # Get ECR registry from destination image
  local ecr_registry="$(echo $dest_image | cut -d'/' -f1)"
  
  # Login to ECR
  echo "Logging in to ECR registry: $ecr_registry"
  aws ecr get-login-password | docker login --username AWS --password-stdin "$ecr_registry"
  
  # Create a temporary auth file for skopeo
  local auth_file=$(mktemp)
  echo "{\"auths\":{\"$ecr_registry\":{\"auth\":\"$(echo -n "AWS:$(aws ecr get-login-password)" | base64)\"}}}" > "$auth_file"
  
  while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt of $max_attempts: Pushing $source_image to $dest_image using skopeo"
    
    # Use skopeo to copy the image
    if skopeo copy --authfile "$auth_file" \
                  --format v2s2 \
                  --dest-tls-verify=true \
                  --src-tls-verify=true \
                  --retry-times 3 \
                  --override-os linux \
                  --override-arch amd64 \
                  docker-daemon:"$source_image" \
                  docker://"$dest_image"; then
      echo "Successfully pushed $source_image to $dest_image using skopeo"
      rm -f "$auth_file"
      return 0
    else
      echo "Push failed, retrying in 10 seconds..."
      sleep 10
      attempt=$((attempt+1))
    fi
  done
  
  rm -f "$auth_file"
  echo "Failed to push $source_image to $dest_image after $max_attempts attempts"
  return 1
}

# Default values
BUILD_IMAGES=false
DEPLOY=false
DELETE=false
PUSH_TO_ECR=false
RUN_TERRAFORM=false

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
      echo "  --delete        Delete from Kubernetes and destroy Terraform infrastructure"
      echo "  --terraform     Run Terraform init, plan, and apply before deployment"
      echo "  --help          Show this help message"
      exit 0
      ;;
    --terraform)
      RUN_TERRAFORM=true
      shift
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

# Run Terraform if requested
if [ "$RUN_TERRAFORM" = true ]; then
  echo "Running Terraform to provision infrastructure..."
  
  # Change to the terraform directory
  cd "$PROJECT_ROOT/terraform"
  
  # Initialize Terraform
  echo "Initializing Terraform..."
  terraform init
  
  # Plan the deployment
  echo "Planning Terraform deployment..."
  terraform plan
  
  # Apply the Terraform configuration
  echo "Applying Terraform configuration..."
  terraform apply -auto-approve
  
  # Change back to the project root directory
  cd "$PROJECT_ROOT"
  
  echo "Terraform infrastructure provisioning completed."
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --no-cli-pager --query Account --output text)
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
  docker buildx build --platform=linux/amd64 --load -t newsagent-django:latest -f django/Dockerfile django/
  
  echo "Building API image for x86_64 architecture..."
  docker buildx build --platform=linux/amd64 --load -t newsagent-api:latest -f core/Dockerfile .
  
  echo "Docker images built successfully."
  echo "Note: MySQL uses the official mysql:8.0 image from Docker Hub, so no build is needed."
fi

# Push Docker images to ECR if requested
if [ "$PUSH_TO_ECR" = true ]; then
  echo "Pushing Docker images to Amazon ECR..."
  
  # Ensure skopeo is installed
  ensure_skopeo_installed
  
  # Create ECR repositories if they don't exist
  echo "Ensuring ECR repositories exist..."
  aws ecr describe-repositories --no-cli-pager --repository-names newsagent-api --region "$AWS_REGION" || \
    aws ecr create-repository --no-cli-pager --repository-name newsagent-api --region "$AWS_REGION"
  
  aws ecr describe-repositories --no-cli-pager --repository-names newsagent-django --region "$AWS_REGION" || \
    aws ecr create-repository --no-cli-pager --repository-name newsagent-django --region "$AWS_REGION"
  
  # Tag images for ECR
  echo "Tagging images for ECR..."
  docker tag newsagent-api:latest "${ECR_REGISTRY}/newsagent-api:latest"
  docker tag newsagent-django:latest "${ECR_REGISTRY}/newsagent-django:latest"
  
  # Push images using skopeo
  echo "Pushing newsagent-api image using skopeo..."
  push_with_skopeo "newsagent-api:latest" "${ECR_REGISTRY}/newsagent-api:latest"
  
  echo "Pushing newsagent-django image using skopeo..."
  push_with_skopeo "newsagent-django:latest" "${ECR_REGISTRY}/newsagent-django:latest"
  
  echo "Docker images pushed to ECR successfully using skopeo with improved reliability."
  
  # Update deployment files to use ECR images
  echo "Updating deployment files to use ECR images..."
  # Update main container and init container in API deployment
  sed -i.bak "s|image: newsagent-api:latest|image: ${ECR_REGISTRY}/newsagent-api:latest|g" k8s/base/deployments/api.yaml
  
  # Update Django deployment
  sed -i.bak "s|image: newsagent-django:latest|image: ${ECR_REGISTRY}/newsagent-django:latest|g" k8s/base/deployments/django.yaml
  
  # Clean up backup files (if any exist)
  find k8s/base/deployments/ -name "*.bak" -type f -delete 2>/dev/null || true
fi

# Function to ensure the Ollama model is properly pulled and loaded
ensure_ollama_model_loaded() {
  local KEY_FILE_PATH=$1
  local OLLAMA_PUBLIC_IP=$2
  local MODEL_NAME=$3
  local MAX_ATTEMPTS=5
  
  echo "Ensuring Ollama model '$MODEL_NAME' is properly pulled and loaded..."
  
  # First, ensure Ollama service is running correctly
  echo "Checking Ollama service status..."
  ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl status ollama-custom.service"
  
  # Restart Ollama service to ensure it's in a clean state
  echo "Restarting Ollama service to ensure clean state..."
  ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl restart ollama-custom.service"
  sleep 15  # Give it more time to fully start
  
  # Verify Ollama is running and listening on all interfaces
  echo "Verifying Ollama is listening on all interfaces..."
  BINDING_OUTPUT=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo netstat -tulpn | grep 11434")
  echo "$BINDING_OUTPUT"
  
  # Check if Ollama is listening on any interfaces (IPv4 or IPv6)
  if echo "$BINDING_OUTPUT" | grep -q "11434"; then
    echo "Ollama is listening on port 11434. Proceeding with model loading..."
    
    # Even if it's not listening on 0.0.0.0 specifically, we'll try to fix it
    if ! echo "$BINDING_OUTPUT" | grep -q "0.0.0.0:11434"; then
      echo "Note: Ollama is not listening on 0.0.0.0 (IPv4 all interfaces), but it may be listening on IPv6 (::)."
      echo "Updating configuration to ensure it listens on all interfaces..."
      
      # Update Ollama configuration
      ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo mkdir -p /etc/ollama"
      ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo bash -c 'echo \"OLLAMA_HOST=0.0.0.0:11434\" > /etc/ollama/config'"
      ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo bash -c 'echo \"OLLAMA_HOST=0.0.0.0:11434\" >> /etc/environment'"
      ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl restart ollama-custom.service"
      sleep 15  # Give it more time to fully start
    fi
  else
    echo "ERROR: Ollama is not listening on any interfaces on port 11434."
    return 1
  fi
  
  # Check if the model is already pulled
  echo "Checking if model '$MODEL_NAME' is already pulled..."
  if ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "ollama list | grep -q '$MODEL_NAME'"; then
    if [ "$MODEL_NAME" == "mistral-nemo" ]; then
      echo "Model 'mistral-nemo' is already pulled. Skipping reinstallation..."
    else
      echo "Model '$MODEL_NAME' is already pulled. Removing it to ensure clean state..."
      ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo ollama rm $MODEL_NAME"
    fi
  fi
  
  echo "Pulling model '$MODEL_NAME'..."
  # Pull the model with multiple attempts
  local attempt=1
  while [ $attempt -le $MAX_ATTEMPTS ]; do
    echo "Attempt $attempt of $MAX_ATTEMPTS: Pulling Ollama model $MODEL_NAME"
    if ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo ollama pull $MODEL_NAME"; then
      echo "Successfully pulled $MODEL_NAME"
      break
    else
      echo "Failed to pull $MODEL_NAME, retrying in 10 seconds..."
      sleep 10
      attempt=$((attempt+1))
    fi
  done
  
  # Verify the model was pulled successfully
  if ! ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "ollama list | grep -q '$MODEL_NAME'"; then
    echo "Error: Failed to pull $MODEL_NAME after $MAX_ATTEMPTS attempts"
    return 1
  fi
  
  # Verify the model is available via the API
  echo "Verifying model availability via API..."
  MODEL_LIST=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "curl -s http://localhost:11434/api/tags")
  echo "Available models: $MODEL_LIST"
  
  if ! echo "$MODEL_LIST" | grep -q "$MODEL_NAME"; then
    echo "Warning: Model '$MODEL_NAME' is not showing up in the API tags list."
    echo "This may cause issues with the API service. Attempting to fix..."
    
    # Restart Ollama service again
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl restart ollama-custom.service"
    sleep 15
    
    # Check again
    MODEL_LIST=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "curl -s http://localhost:11434/api/tags")
    if ! echo "$MODEL_LIST" | grep -q "$MODEL_NAME"; then
      echo "Error: Model '$MODEL_NAME' is still not showing up in the API tags list."
      return 1
    fi
  fi
  
  # Test the model with a simple query to ensure it's working
  echo "Testing model '$MODEL_NAME' with a simple query..."
  local TEST_RESPONSE=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "curl -s -X POST http://localhost:11434/api/generate -d '{\"model\":\"$MODEL_NAME\",\"prompt\":\"Hello, world!\",\"stream\":false}'")
  
  # Check if the response contains the expected fields
  if echo "$TEST_RESPONSE" | grep -q "response"; then
    echo "Model '$MODEL_NAME' is working properly!"
    
    # Test external connectivity
    echo "Testing external connectivity to the model..."
    EXTERNAL_TEST=$(curl -s -X POST \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"$MODEL_NAME\",\"prompt\":\"Hello, world!\",\"stream\":false}" \
      "http://$OLLAMA_PUBLIC_IP:11434/api/generate")
    
    if echo "$EXTERNAL_TEST" | grep -q "response"; then
      echo "External connectivity test successful!"
    else
      echo "Warning: External connectivity test failed. Response: $EXTERNAL_TEST"
      echo "This may indicate network or firewall issues."
    fi
    
    return 0
  else
    echo "Warning: Model '$MODEL_NAME' did not respond as expected. Response: $TEST_RESPONSE"
    
    # Try one more restart
    echo "Attempting one final fix by restarting Ollama service..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl restart ollama-custom.service"
    sleep 20
    
    # Test again after restart
    TEST_RESPONSE=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "curl -s -X POST http://localhost:11434/api/generate -d '{\"model\":\"$MODEL_NAME\",\"prompt\":\"Hello, world!\",\"stream\":false}'")
    
    if echo "$TEST_RESPONSE" | grep -q "response"; then
      echo "Model '$MODEL_NAME' is now working properly after service restart!"
      return 0
    else
      echo "Error: Model '$MODEL_NAME' is still not responding correctly after service restart."
      echo "Response: $TEST_RESPONSE"
      return 1
    fi
  fi
}

# Get Ollama instance information and install Ollama
# Using a more efficient approach based on test.sh
setup_and_configure_ollama() {
  echo "Getting Ollama instance information..."
  
  # Get the instance ID with the tag Name=ollama-gpu-instance and state=running
  OLLAMA_INSTANCE_ID=$(aws ec2 describe-instances --no-cli-pager --filters "Name=tag:Name,Values=ollama-gpu-instance" "Name=instance-state-name,Values=running" --query "Reservations[0].Instances[0].InstanceId" --output text)
  
  if [ -z "$OLLAMA_INSTANCE_ID" ] || [ "$OLLAMA_INSTANCE_ID" == "None" ]; then
    echo "Error: Could not find Ollama instance with tag Name=ollama-gpu-instance"
    exit 1
  fi
  
  # Get the public IP of the Ollama instance
  OLLAMA_PUBLIC_IP=$(aws ec2 describe-instances --no-cli-pager --instance-ids "$OLLAMA_INSTANCE_ID" --query "Reservations[0].Instances[0].PublicIpAddress" --output text)
  
  if [ -z "$OLLAMA_PUBLIC_IP" ] || [ "$OLLAMA_PUBLIC_IP" == "None" ]; then
    echo "Error: Could not get public IP of Ollama instance"
    exit 1
  fi
  
  # Also get the private IP for EKS internal communication
  OLLAMA_PRIVATE_IP=$(aws ec2 describe-instances --no-cli-pager --instance-ids "$OLLAMA_INSTANCE_ID" --query "Reservations[0].Instances[0].PrivateIpAddress" --output text)
  
  if [ -z "$OLLAMA_PRIVATE_IP" ] || [ "$OLLAMA_PRIVATE_IP" == "None" ]; then
    echo "Error: Could not get private IP of Ollama instance"
    exit 1
  fi
  
  echo "Found Ollama instance with ID $OLLAMA_INSTANCE_ID, public IP $OLLAMA_PUBLIC_IP, and private IP $OLLAMA_PRIVATE_IP"
  
  # Get the key file path from terraform output
  KEY_FILE_PATH=$(cd terraform && terraform output -raw ollama_key_path 2>/dev/null || echo "terraform/ollama-key.pem")
  
  if [ ! -f "$KEY_FILE_PATH" ]; then
    KEY_FILE_PATH="terraform/ollama-key.pem"
  fi
  
  echo "Using SSH key: $KEY_FILE_PATH"
  
  # Ensure the key has the correct permissions
  chmod 600 "$KEY_FILE_PATH"
  
  # Install Ollama on the instance
  echo "Installing Ollama on the instance..."
  
  # Check if Ollama is already installed and running
  echo "Checking if Ollama is already installed and running..."
  if ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "command -v ollama > /dev/null && sudo systemctl is-active --quiet ollama-custom.service"; then
    echo "Ollama is already installed and running. Skipping installation but ensuring model is loaded..."
    
    # Even if Ollama is already installed, we still need to ensure the model is properly loaded
    ensure_ollama_model_loaded "$KEY_FILE_PATH" "$OLLAMA_PUBLIC_IP" "mistral-nemo"
    return 0
  fi
  
  # Create a temporary script file
  TEMP_SCRIPT=$(mktemp)
  cat > "$TEMP_SCRIPT" << 'EOL'
#!/bin/bash
set -e

# Check if Ollama is already installed
if command -v ollama > /dev/null; then
  echo "Ollama is already installed. Checking if it's running..."
  
  # Check if Ollama is running and listening on port 11434
  if sudo netstat -tulpn | grep 11434 > /dev/null; then
    echo "Ollama is already running and listening on port 11434."
    exit 0
  else
    echo "Ollama is installed but not running. Configuring and starting Ollama..."
  fi
else
  echo "Ollama is not installed. Installing Ollama..."
  
  # Install required packages
  sudo apt-get update
  sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    jq \
    net-tools \
    ufw
    
  # Install NVIDIA drivers and CUDA for GPU support
  echo "Installing NVIDIA drivers and CUDA for GPU support..."
  sudo apt-get install -y linux-headers-$(uname -r)
  distribution=$(. /etc/os-release;echo $ID$VERSION_ID | sed -e 's/\.//g')
  wget https://developer.download.nvidia.com/compute/cuda/repos/$distribution/x86_64/cuda-keyring_1.0-1_all.deb
  sudo dpkg -i cuda-keyring_1.0-1_all.deb
  sudo apt-get update
  sudo apt-get -y install cuda-drivers
  sudo apt-get -y install cuda
  
  # Verify NVIDIA installation
  echo "Verifying NVIDIA driver installation..."
  if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA drivers installed successfully:"
    nvidia-smi
  else
    echo "WARNING: NVIDIA drivers installation may have failed. Ollama may not use GPU acceleration."
  fi
    
  # Configure firewall to allow Ollama port
  echo "Configuring firewall to allow port 11434..."
  sudo ufw allow 22/tcp
  sudo ufw allow 11434/tcp
  
  # Enable firewall if not already enabled (don't enable if it would break SSH connection)
  if ! sudo ufw status | grep -q "Status: active"; then
    echo "Enabling firewall..."
    # Enable firewall without confirmation prompt
    echo "y" | sudo ufw enable
  fi
  
  # Verify firewall rules
  echo "Verifying firewall rules..."
  sudo ufw status
fi

# Completely remove any existing Ollama installation to ensure clean setup
if command -v ollama > /dev/null; then
  echo "Removing existing Ollama installation..."
  sudo systemctl stop ollama.service 2>/dev/null || true
  sudo systemctl stop ollama-custom.service 2>/dev/null || true
  sudo systemctl disable ollama.service 2>/dev/null || true
  sudo systemctl disable ollama-custom.service 2>/dev/null || true
  sudo rm -f /etc/systemd/system/ollama.service.d/override.conf 2>/dev/null || true
  sudo rm -f /etc/systemd/system/ollama-custom.service 2>/dev/null || true
  sudo systemctl daemon-reload
fi

# Create Ollama configuration directory and set binding to all interfaces
echo "Creating Ollama configuration..."
sudo mkdir -p /etc/ollama
sudo bash -c 'cat > /etc/ollama/config << EOL
OLLAMA_HOST=0.0.0.0:11434
# Enable GPU acceleration
OLLAMA_CUDA=1
EOL'
sudo chmod 644 /etc/ollama/config
cat /etc/ollama/config

# Set environment variables globally and for current session
echo "Setting Ollama environment variables..."
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_CUDA=1
echo "export OLLAMA_HOST=0.0.0.0:11434" >> ~/.bashrc
echo "export OLLAMA_CUDA=1" >> ~/.bashrc
sudo bash -c 'echo "export OLLAMA_HOST=0.0.0.0:11434" >> /etc/profile'
sudo bash -c 'echo "export OLLAMA_CUDA=1" >> /etc/profile'
sudo bash -c 'echo "OLLAMA_HOST=0.0.0.0:11434" >> /etc/environment'
sudo bash -c 'echo "OLLAMA_CUDA=1" >> /etc/environment'
echo "Current OLLAMA_HOST value: $OLLAMA_HOST"
echo "Current OLLAMA_CUDA value: $OLLAMA_CUDA"

# Set up CUDA environment variables
echo "Setting up CUDA environment variables..."
sudo bash -c 'echo "export PATH=/usr/local/cuda/bin:\$PATH" > /etc/profile.d/cuda.sh'
sudo bash -c 'echo "export LD_LIBRARY_PATH=/usr/local/cuda/lib64:\$LD_LIBRARY_PATH" >> /etc/profile.d/cuda.sh'
sudo chmod +x /etc/profile.d/cuda.sh
source /etc/profile.d/cuda.sh
echo "PATH now includes CUDA: $PATH"

# Install Ollama
echo "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Find the correct path to the Ollama executable
OLLAMA_EXEC_PATH=$(which ollama)
echo "Found Ollama executable at: $OLLAMA_EXEC_PATH"

# Create a custom systemd service for Ollama that explicitly binds to all interfaces and enables GPU
echo "Creating custom systemd service for Ollama..."
sudo bash -c "cat > /etc/systemd/system/ollama-custom.service << EOL
[Unit]
Description=Ollama API Service
After=network-online.target
Wants=network-online.target

[Service]
Environment=\"OLLAMA_HOST=0.0.0.0:11434\"
Environment=\"OLLAMA_CUDA=1\"
Environment=\"PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"
Environment=\"LD_LIBRARY_PATH=/usr/local/cuda/lib64\"
ExecStart=$OLLAMA_EXEC_PATH serve
Restart=always
RestartSec=3
User=root
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOL"

# Reload systemd, disable default service, enable and start custom service
echo "Configuring systemd services..."
sudo systemctl daemon-reload
sudo systemctl stop ollama.service 2>/dev/null || true
sudo systemctl disable ollama.service 2>/dev/null || true
sudo systemctl enable ollama-custom.service
sudo systemctl restart ollama-custom.service

# Verify the service is running with the correct configuration
echo "Verifying Ollama service configuration..."
sudo systemctl status ollama-custom.service
sudo grep -r "OLLAMA_HOST\|OLLAMA_CUDA" /etc/systemd/ /etc/ollama/ /etc/environment

# Wait for Ollama service to start
echo "Waiting for Ollama service to start..."
for i in {1..30}; do
  if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "Ollama service is up and running"
    break
  fi
  echo "Waiting for Ollama service... ($i/30)"
  sleep 2
done

# Verify Ollama is listening on all interfaces
echo "Checking Ollama binding..."
netstat -tulpn | grep 11434

# Pull the mistral-nemo model with retry mechanism
echo "Pulling Ollama model: mistral-nemo"
max_attempts=3
attempt=1

while [ $attempt -le $max_attempts ]; do
  echo "Attempt $attempt of $max_attempts: Pulling Ollama model mistral-nemo"
  if sudo OLLAMA_CUDA=1 ollama pull mistral-nemo; then
    echo "Successfully pulled mistral-nemo"
    break
  else
    echo "Failed to pull mistral-nemo, retrying in 10 seconds..."
    sleep 10
    attempt=$((attempt+1))
  fi
done

# Verify the model was pulled successfully
if ! ollama list | grep -q "mistral-nemo"; then
  echo "Error: Failed to pull mistral-nemo after $max_attempts attempts"
  exit 1
fi

# Verify GPU usage
echo "Verifying GPU usage by Ollama..."
if nvidia-smi | grep -q ollama; then
  echo "SUCCESS: Ollama is using the GPU"
  nvidia-smi | grep ollama
else
  echo "WARNING: Ollama process not detected in nvidia-smi output. This may indicate Ollama is not using the GPU."
  echo "Restarting Ollama service to ensure GPU detection..."
  sudo systemctl restart ollama-custom.service
  sleep 15
  
  # Check again after restart
  if nvidia-smi | grep -q ollama; then
    echo "SUCCESS: After restart, Ollama is now using the GPU"
    nvidia-smi | grep ollama
  else
    echo "WARNING: Ollama still not detected in nvidia-smi output after restart."
    echo "Running a test query to load the model into GPU memory..."
    curl -s -X POST http://localhost:11434/api/generate -d '{"model":"mistral-nemo","prompt":"Hello, world!","stream":false}' > /dev/null
    sleep 5
    
    # Check one more time
    if nvidia-smi | grep -q ollama; then
      echo "SUCCESS: After test query, Ollama is now using the GPU"
      nvidia-smi | grep ollama
    else
      echo "WARNING: Ollama still not detected in nvidia-smi output after test query."
      echo "This may indicate a configuration issue with GPU support."
    fi
  fi
fi

# Final verification
echo "Final verification of Ollama service:"
sudo systemctl status ollama-custom.service
netstat -tulpn | grep 11434
EOL
  
  # Copy the script to the instance
  scp -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" "$TEMP_SCRIPT" ubuntu@"$OLLAMA_PUBLIC_IP":/tmp/install_ollama.sh
  
  # Execute the script on the instance
  ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "chmod +x /tmp/install_ollama.sh && sudo /tmp/install_ollama.sh"
  
  # Clean up the temporary script
  rm "$TEMP_SCRIPT"
  
  # Verify Ollama is running and accessible locally on the instance
  echo "Verifying Ollama is running and accessible locally on the instance..."
  if ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "curl -s http://localhost:11434/api/tags > /dev/null"; then
    echo "Ollama is running and accessible locally."
  else
    echo "Warning: Ollama may not be running or accessible locally. Attempting to restart service..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl restart ollama-custom.service"
    sleep 10
    
    # Check again after restart
    if ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "curl -s http://localhost:11434/api/tags > /dev/null"; then
      echo "Ollama is now running and accessible after service restart."
    else
      echo "Error: Ollama is still not accessible after service restart. Deployment may fail."
    fi
  fi
  
  # Verify Ollama is listening on all interfaces
  echo "Verifying Ollama is listening on all interfaces..."
  BINDING_OUTPUT=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo netstat -tulpn | grep 11434")
  echo "$BINDING_OUTPUT"
  
  # Check if Ollama is listening on 0.0.0.0 (all interfaces)
  if echo "$BINDING_OUTPUT" | grep -q "0.0.0.0:11434"; then
    echo "Ollama is correctly listening on all interfaces (0.0.0.0)."
  else
    echo "WARNING: Ollama is not listening on all interfaces. Attempting to fix..."
    
    # Force restart with explicit binding - with detailed debugging
    echo "Stopping any running Ollama services..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl stop ollama.service 2>/dev/null || true"
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl stop ollama-custom.service 2>/dev/null || true"
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo killall -9 ollama 2>/dev/null || true"
    
    echo "Checking Ollama executable location..."
    OLLAMA_PATH=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "which ollama")
    echo "Ollama executable found at: $OLLAMA_PATH"
    
    echo "Updating Ollama configuration..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo bash -c 'echo \"OLLAMA_HOST=0.0.0.0:11434\" > /etc/ollama/config'"
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo bash -c 'echo \"OLLAMA_HOST=0.0.0.0:11434\" >> /etc/environment'"
    
    echo "Creating updated systemd service file with correct executable path and GPU support..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo bash -c 'cat > /etc/systemd/system/ollama-custom.service << EOL
[Unit]
Description=Ollama API Service
After=network-online.target
Wants=network-online.target

[Service]
Environment=\"OLLAMA_HOST=0.0.0.0:11434\"
Environment=\"OLLAMA_CUDA=1\"
ExecStart=$OLLAMA_PATH serve
Restart=always
RestartSec=3
User=root
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOL'"
    
    echo "Reloading systemd and restarting Ollama..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl daemon-reload"
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl restart ollama-custom.service"
    
    # Wait a bit longer for the service to fully start
    echo "Waiting for service to start..."
    sleep 10
    
    # Check again after fix
    echo "Checking binding again after fix..."
    sleep 5
    BINDING_OUTPUT_AFTER=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo netstat -tulpn | grep 11434")
    echo "$BINDING_OUTPUT_AFTER"
    
    if echo "$BINDING_OUTPUT_AFTER" | grep -q "0.0.0.0:11434"; then
      echo "Fix successful! Ollama is now listening on all interfaces (0.0.0.0)."
    else
      echo "WARNING: Fix attempt failed. Ollama is still not listening on all interfaces."
      echo "Checking configuration and service status..."
      ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "cat /etc/ollama/config"
      ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl status ollama-custom.service"
    fi
  fi
  
  # Verify external connectivity to Ollama
  echo "Verifying external connectivity to Ollama (this may take a few seconds)..."
  if command -v nc > /dev/null; then
    if timeout 5 nc -z -v "$OLLAMA_PUBLIC_IP" 11434 2>/dev/null; then
      echo "Success: Ollama is accessible from outside the instance on port 11434."
    else
      echo "Warning: Could not connect to Ollama from outside the instance on port 11434."
      echo "This may be due to network restrictions or firewall settings."
      echo "Checking EC2 security group rules..."
      aws ec2 describe-security-groups --no-cli-pager --group-ids $(aws ec2 describe-instances --no-cli-pager --instance-ids "$OLLAMA_INSTANCE_ID" --query "Reservations[0].Instances[0].SecurityGroups[0].GroupId" --output text) --query "SecurityGroups[0].IpPermissions[?FromPort==\`11434\`]"
    fi
  else
    echo "Warning: 'nc' command not found. Skipping external connectivity check."
    echo "To manually check connectivity, run: telnet $OLLAMA_PUBLIC_IP 11434"
  fi
  
  echo "Ollama installation completed successfully."
  
  # Ensure the mistral-nemo model is properly pulled and loaded
  ensure_ollama_model_loaded "$KEY_FILE_PATH" "$OLLAMA_PUBLIC_IP" "mistral-nemo"
  
  # Verify the model is available via the API
  echo "Verifying model availability via API..."
  MODEL_LIST=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "curl -s http://localhost:11434/api/tags")
  echo "Available models: $MODEL_LIST"
  
  # Verify GPU usage
  echo "Verifying GPU usage by Ollama..."
  GPU_CHECK=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "nvidia-smi | grep -i ollama")
  if [ -n "$GPU_CHECK" ]; then
    echo "SUCCESS: Ollama is using the GPU:"
    echo "$GPU_CHECK"
  else
    echo "WARNING: Ollama process not detected in nvidia-smi output. This may indicate Ollama is not using the GPU."
    echo "Checking if any process is using the GPU..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "nvidia-smi"
    
    echo "Checking CUDA environment variables..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "grep -r OLLAMA_CUDA /etc/ollama/ /etc/environment /etc/systemd/system/ollama-custom.service"
    
    echo "Setting up CUDA environment variables..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo bash -c 'echo \"export PATH=/usr/local/cuda/bin:\\\$PATH\" > /etc/profile.d/cuda.sh'"
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo bash -c 'echo \"export LD_LIBRARY_PATH=/usr/local/cuda/lib64:\\\$LD_LIBRARY_PATH\" >> /etc/profile.d/cuda.sh'"
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo chmod +x /etc/profile.d/cuda.sh"
    
    echo "Updating Ollama service with CUDA paths..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo bash -c 'cat > /etc/systemd/system/ollama-custom.service << EOL
[Unit]
Description=Ollama API Service
After=network-online.target
Wants=network-online.target

[Service]
Environment=\"OLLAMA_HOST=0.0.0.0:11434\"
Environment=\"OLLAMA_CUDA=1\"
Environment=\"PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"
Environment=\"LD_LIBRARY_PATH=/usr/local/cuda/lib64\"
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3
User=root
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOL'"
    
    echo "Restarting Ollama service with updated configuration..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo systemctl daemon-reload && sudo systemctl restart ollama-custom.service"
    sleep 15
    
    # Check again after restart
    GPU_CHECK_AFTER=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "nvidia-smi | grep -i ollama")
    if [ -n "$GPU_CHECK_AFTER" ]; then
      echo "SUCCESS: After restart, Ollama is now using the GPU:"
      echo "$GPU_CHECK_AFTER"
    else
      echo "WARNING: Ollama still not detected in nvidia-smi output after restart."
      echo "Running a test query to load the model into GPU memory..."
      ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "curl -s -X POST http://localhost:11434/api/generate -d '{\"model\":\"mistral-nemo\",\"prompt\":\"Hello, world!\",\"stream\":false}' > /dev/null"
      sleep 5
      
      # Check one more time
      GPU_CHECK_FINAL=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "nvidia-smi | grep -i ollama")
      if [ -n "$GPU_CHECK_FINAL" ]; then
        echo "SUCCESS: After test query, Ollama is now using the GPU:"
        echo "$GPU_CHECK_FINAL"
      else
        echo "WARNING: Ollama still not detected in nvidia-smi output after test query."
        echo "This may indicate a configuration issue with GPU support."
      fi
    fi
  fi
  
  if echo "$MODEL_LIST" | grep -q "mistral-nemo"; then
    echo "Model 'mistral-nemo' is available via the API."
  else
    echo "Warning: Model 'mistral-nemo' is not showing up in the API tags list."
    echo "This may cause issues with the API service. Attempting to fix..."
    
    # Try to pull the model again with force
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo ollama rm mistral-nemo 2>/dev/null || true"
    ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "sudo ollama pull mistral-nemo"
    
    # Check again
    MODEL_LIST=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE_PATH" ubuntu@"$OLLAMA_PUBLIC_IP" "curl -s http://localhost:11434/api/tags")
    if echo "$MODEL_LIST" | grep -q "mistral-nemo"; then
      echo "Success! Model 'mistral-nemo' is now available via the API."
    else
      echo "Error: Model 'mistral-nemo' is still not showing up in the API tags list."
      echo "The API service may not work correctly. Please check the Ollama instance manually."
    fi
  fi
}

# Deploy to Kubernetes if requested
if [ "$DEPLOY" = true ]; then
  echo "Deploying to Kubernetes..."
  
  # Update kubeconfig to point to the EKS cluster
  echo "Updating kubeconfig to point to the EKS cluster..."
  CLUSTER_NAME=$(aws eks list-clusters --no-cli-pager --query "clusters[0]" --output text)
  if [ -z "$CLUSTER_NAME" ] || [ "$CLUSTER_NAME" == "None" ]; then
    echo "Error: Could not find any EKS clusters. Make sure you've run terraform apply first."
    exit 1
  fi
  
  echo "Found EKS cluster: $CLUSTER_NAME"
  aws eks update-kubeconfig --no-cli-pager --name "$CLUSTER_NAME" --region "$AWS_REGION"
  echo "Kubeconfig updated successfully."
  
  # Verify connection to the cluster
  echo "Verifying connection to the cluster..."
  kubectl cluster-info
  if [ $? -ne 0 ]; then
    echo "Error: Could not connect to the EKS cluster. Check your AWS credentials and try again."
    exit 1
  fi
  
  # Setup and configure Ollama
  setup_and_configure_ollama
  
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
  
  echo "Deploying Ollama service..."
  # Create a temporary file with the OLLAMA_PUBLIC_IP placeholder replaced
  TMP_OLLAMA_SERVICE=$(mktemp)
  cat k8s/base/services/ollama.yaml | sed "s|\${OLLAMA_PUBLIC_IP}|${OLLAMA_PUBLIC_IP}|g" > "$TMP_OLLAMA_SERVICE"
  kubectl apply -f "$TMP_OLLAMA_SERVICE"
  rm -f "$TMP_OLLAMA_SERVICE"
  
  echo "Deploying Django and API applications..."
  kubectl apply -f k8s/base/deployments/django.yaml
  kubectl apply -f k8s/base/deployments/api.yaml
  
  # Apply services
  kubectl apply -f k8s/base/services/django.yaml
  kubectl apply -f k8s/base/services/api.yaml
  
  echo "Deploying Ingress..."
  kubectl apply -f k8s/base/ingress.yaml
  
  echo "Deployment completed successfully."
  
  # Display resources
  echo "Resources in namespace 'newsagent':"
  kubectl get all -n newsagent
  
  # Wait for load balancers to be provisioned
  echo ""
  echo "Waiting for load balancers to be provisioned (this may take a few minutes)..."
  
  # Function to wait for external IP/hostname
  wait_for_external_ip() {
    local service_name=$1
    local namespace=$2
    local max_attempts=15  # Reduced from 30 to speed up deployment
    local attempt=1
    local external_ip=""
    
    while [ $attempt -le $max_attempts ]; do
      echo "Checking external IP for $service_name (attempt $attempt/$max_attempts)..."
      external_ip=$(kubectl get service $service_name -n $namespace --template='{{range .status.loadBalancer.ingress}}{{.hostname}}{{end}}')
      
      if [ -n "$external_ip" ]; then
        echo "External hostname found for $service_name: $external_ip"
        return 0
      else
        echo "External hostname not yet available, waiting..."
        sleep 10
        attempt=$((attempt+1))
      fi
    done
    
    echo "Warning: Failed to get external hostname for $service_name after $max_attempts attempts"
    echo "Continuing with deployment, but some features may not work correctly."
    return 0  # Return success anyway to continue the script
  }
  
  # Wait for Django and API services to get external IPs in parallel
  echo "Waiting for Django service external IP..."
  wait_for_external_ip "django" "newsagent" &
  DJANGO_WAIT_PID=$!
  
  echo "Waiting for API service external IP..."
  wait_for_external_ip "api" "newsagent" &
  API_WAIT_PID=$!
  
  # Wait for both processes to complete
  wait $DJANGO_WAIT_PID
  wait $API_WAIT_PID
  
  # Get API hostname and OLLAMA_PUBLIC_IP to update ConfigMap
  API_HOSTNAME=$(kubectl get service api -n newsagent --template='{{range .status.loadBalancer.ingress}}{{.hostname}}{{end}}')
  
  # Update ConfigMap with both API_HOSTNAME and OLLAMA_PUBLIC_IP
  if [ -n "$API_HOSTNAME" ] && [ -n "$OLLAMA_PUBLIC_IP" ]; then
    echo "Updating ConfigMap with API hostname: $API_HOSTNAME and OLLAMA_PUBLIC_IP: $OLLAMA_PUBLIC_IP"
    
    # Create a temporary file with the updated configmap
    TMP_CONFIGMAP=$(mktemp)
    cat k8s/base/configmaps/app-config.yaml | \
      sed "s|\${API_HOSTNAME}|${API_HOSTNAME}|g" | \
      sed "s|\${api_hostname}|${API_HOSTNAME}|g" | \
      sed "s|\${OLLAMA_PUBLIC_IP}|${OLLAMA_PUBLIC_IP}|g" > "$TMP_CONFIGMAP"
    
    # Apply the updated configmap
    kubectl apply -f "$TMP_CONFIGMAP"
    
    # Clean up the temporary file
    rm -f "$TMP_CONFIGMAP"
    
    # Verify the ConfigMap was updated correctly
    echo "Verifying ConfigMap was updated correctly..."
    kubectl get configmap app-config -n newsagent -o yaml | grep -A 1 "API_URL:"
    
    # Restart both API and Django deployments to pick up the new configmap values
    echo "Restarting API and Django deployments to pick up new configmap values..."
    kubectl rollout restart deployment api -n newsagent
    kubectl rollout restart deployment django -n newsagent
    
    echo "ConfigMap updated successfully and deployments restarted."
  elif [ -n "$API_HOSTNAME" ]; then
    echo "Updating ConfigMap with API hostname: $API_HOSTNAME"
    
    # Create a temporary file with the updated configmap
    TMP_CONFIGMAP=$(mktemp)
    cat k8s/base/configmaps/app-config.yaml | \
      sed "s|\${API_HOSTNAME}|${API_HOSTNAME}|g" | \
      sed "s|\${api_hostname}|${API_HOSTNAME}|g" > "$TMP_CONFIGMAP"
    
    # Apply the updated configmap
    kubectl apply -f "$TMP_CONFIGMAP"
    
    # Clean up the temporary file
    rm -f "$TMP_CONFIGMAP"
    
    # Verify the ConfigMap was updated correctly
    echo "Verifying ConfigMap was updated correctly..."
    kubectl get configmap app-config -n newsagent -o yaml | grep -A 1 "API_URL:"
    
    # Restart both API and Django deployments to pick up the new configmap values
    echo "Restarting API and Django deployments to pick up new configmap values..."
    kubectl rollout restart deployment api -n newsagent
    kubectl rollout restart deployment django -n newsagent
    
    echo "ConfigMap updated with API_HOSTNAME only and deployments restarted. OLLAMA_PUBLIC_IP not available."
  elif [ -n "$OLLAMA_PUBLIC_IP" ]; then
    echo "Updating ConfigMap with OLLAMA_PUBLIC_IP: $OLLAMA_PUBLIC_IP"
    
    # Create a temporary file with the updated configmap
    TMP_CONFIGMAP=$(mktemp)
    cat k8s/base/configmaps/app-config.yaml | \
      sed "s|\${OLLAMA_PUBLIC_IP}|${OLLAMA_PUBLIC_IP}|g" > "$TMP_CONFIGMAP"
    
    # Apply the updated configmap
    kubectl apply -f "$TMP_CONFIGMAP"
    
    # Clean up the temporary file
    rm -f "$TMP_CONFIGMAP"
    
    # Verify the ConfigMap was updated correctly
    echo "Verifying ConfigMap was updated correctly..."
    kubectl get configmap app-config -n newsagent -o yaml | grep -A 1 "OLLAMA_BASE_URL:"
    
    # Restart both API and Django deployments to pick up the new configmap values
    echo "Restarting API and Django deployments to pick up new configmap values..."
    kubectl rollout restart deployment api -n newsagent
    kubectl rollout restart deployment django -n newsagent
    
    echo "ConfigMap updated with OLLAMA_PUBLIC_IP only and deployments restarted. API_HOSTNAME not available."
  else
    echo "Warning: Could not get API hostname or OLLAMA_PUBLIC_IP. ConfigMap not updated."
  fi
  
  # Update Ollama service Endpoints with OLLAMA_PUBLIC_IP
  if [ -n "$OLLAMA_PUBLIC_IP" ]; then
    echo "Updating Ollama service Endpoints with OLLAMA_PUBLIC_IP: $OLLAMA_PUBLIC_IP"
    kubectl get endpoints ollama -n newsagent -o yaml | \
      sed "s|\${OLLAMA_PUBLIC_IP}|${OLLAMA_PUBLIC_IP}|g" | \
      kubectl apply -f -
    echo "Ollama service Endpoints updated successfully."
  else
    echo "Warning: Could not get OLLAMA_PUBLIC_IP. Ollama service Endpoints not updated."
  fi
  
  # Get and display the URLs
  echo ""
  echo "============================================================"
  echo "                   ACCESS INFORMATION                       "
  echo "============================================================"
  echo "Your application is now accessible at the following URLs:"
  echo ""
  
  # Get Django URL
  DJANGO_HOSTNAME=$(kubectl get service django -n newsagent --template='{{range .status.loadBalancer.ingress}}{{.hostname}}{{end}}')
  if [ -n "$DJANGO_HOSTNAME" ]; then
    echo "Django Frontend: http://$DJANGO_HOSTNAME:8000"
  else
    echo "Django Frontend: URL not available yet. Run 'kubectl get service django -n newsagent' to check status."
  fi
  
  # Get API URL
  API_HOSTNAME=$(kubectl get service api -n newsagent --template='{{range .status.loadBalancer.ingress}}{{.hostname}}{{end}}')
  if [ -n "$API_HOSTNAME" ]; then
    echo "API Endpoint: http://$API_HOSTNAME:8001"
    echo "API Documentation: http://$API_HOSTNAME:8001/docs"
  else
    echo "API Endpoint: URL not available yet. Run 'kubectl get service api -n newsagent' to check status."
  fi
  
  echo "============================================================"
  echo "Note: It may take a few minutes for DNS to propagate and for the services to be fully accessible."
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
  
  # Run Terraform destroy to clean up infrastructure
  echo "Running Terraform destroy to clean up infrastructure..."
  cd "$PROJECT_ROOT/terraform"
  terraform destroy -auto-approve
  cd "$PROJECT_ROOT"
  
  echo "Deletion completed successfully."
fi

echo "Done."
