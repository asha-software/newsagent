terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
  required_version = ">= 1.2.0"
}

provider "aws" {
  region = var.aws_region
  # Using environment variables from core/.env
  # Terraform automatically checks for AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
}

# Data source for availability zones
data "aws_availability_zones" "available" {}

# VPC for EKS
resource "aws_vpc" "eks_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-vpc"
    }
  )
}

# Internet Gateway
resource "aws_internet_gateway" "eks_igw" {
  vpc_id = aws_vpc.eks_vpc.id
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-igw"
    }
  )
}

# Public Subnets
resource "aws_subnet" "eks_public_subnet" {
  count                   = 2
  vpc_id                  = aws_vpc.eks_vpc.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  map_public_ip_on_launch = true
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-public-subnet-${count.index}"
      "kubernetes.io/role/elb" = "1"
      "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    }
  )
}

# Security Group for EKS Cluster Load Balancers
resource "aws_security_group" "eks_lb_sg" {
  name        = "${var.cluster_name}-lb-sg"
  description = "Security group for EKS cluster load balancers"
  vpc_id      = aws_vpc.eks_vpc.id

  # Allow HTTP traffic for Django (port 8000)
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow Django HTTP traffic"
  }

  # Allow HTTP traffic for API (port 8001)
  ingress {
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow API HTTP traffic"
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-lb-sg"
    }
  )
}

# Route Table for Public Subnets
resource "aws_route_table" "eks_public_rt" {
  vpc_id = aws_vpc.eks_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.eks_igw.id
  }
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-public-rt"
    }
  )
}

# Route Table Association for Public Subnets
resource "aws_route_table_association" "eks_public_rt_assoc" {
  count          = length(aws_subnet.eks_public_subnet)
  subnet_id      = aws_subnet.eks_public_subnet[count.index].id
  route_table_id = aws_route_table.eks_public_rt.id
}

# IAM Role for EKS Cluster - Use a unique name to avoid conflicts
resource "aws_iam_role" "eks_cluster_role" {
  name = "${var.cluster_name}-cluster-role-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })
}

# Attach Required Policies to Cluster Role
resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  
  # This ensures the policy attachment is recreated when the role is recreated
  lifecycle {
    create_before_destroy = true
  }
}

# EKS Cluster
resource "aws_eks_cluster" "eks_cluster" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = aws_subnet.eks_public_subnet[*].id
    endpoint_private_access = var.endpoint_private_access
    endpoint_public_access  = var.endpoint_public_access
    security_group_ids      = [aws_security_group.eks_lb_sg.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_instance.ollama_instance  # Add dependency on EC2 instance to create it first
  ]
}

# IAM Role for EKS Node Group - Use a unique name to avoid conflicts
resource "aws_iam_role" "eks_node_role" {
  name = "${var.cluster_name}-node-role-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# Attach Required Policies to Node Role
resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  
  # This ensures the policy attachment is recreated when the role is recreated
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  
  # This ensures the policy attachment is recreated when the role is recreated
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_iam_role_policy_attachment" "eks_container_registry_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  
  # This ensures the policy attachment is recreated when the role is recreated
  lifecycle {
    create_before_destroy = true
  }
}

# EKS Managed Node Group - No AMI ID Required!
resource "aws_eks_node_group" "eks_node_group" {
  cluster_name    = aws_eks_cluster.eks_cluster.name
  node_group_name = "${var.cluster_name}-node-group"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = aws_subnet.eks_public_subnet[*].id
  
  # Instance type for the nodes
  instance_types = [var.node_instance_type]
  
  # Scaling configuration
  scaling_config {
    desired_size = var.node_desired_size
    max_size     = var.node_max_size
    min_size     = var.node_min_size
  }
  
  # Optional: Add labels to your nodes
  labels = {
    role = "general"
  }
  
  # Configure remote access to nodes using our generated key pair
  remote_access {
    ec2_ssh_key = aws_key_pair.ollama_key_pair.key_name
    source_security_group_ids = var.source_security_group_ids
  }
  
  # Add lifecycle configuration to handle key pair issues
  lifecycle {
    ignore_changes = [remote_access]
  }
  
  # Ensure IAM role policies are attached before creating node group
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
    aws_instance.ollama_instance  # Add dependency on EC2 instance to create it first
  ]
}

# Output the EKS Cluster Endpoint and Certificate Authority
output "eks_cluster_endpoint" {
  value = aws_eks_cluster.eks_cluster.endpoint
}

output "eks_cluster_certificate_authority" {
  value = aws_eks_cluster.eks_cluster.certificate_authority[0].data
}

# Output command to update kubeconfig
output "kubeconfig_update_command" {
  value = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.eks_cluster.name}"
}

# Public Subnet for Ollama EC2 Instance
resource "aws_subnet" "ollama_public_subnet" {
  vpc_id                  = aws_vpc.eks_vpc.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 10) # Using a different subnet range
  map_public_ip_on_launch = true
  availability_zone       = data.aws_availability_zones.available.names[0]
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-ollama-public-subnet"
    }
  )
}

# Route Table for Ollama Public Subnet
resource "aws_route_table" "ollama_public_rt" {
  vpc_id = aws_vpc.eks_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.eks_igw.id
  }
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-ollama-public-rt"
    }
  )
}

# Route Table Association for Ollama Public Subnet
resource "aws_route_table_association" "ollama_public_rt_assoc" {
  subnet_id      = aws_subnet.ollama_public_subnet.id
  route_table_id = aws_route_table.ollama_public_rt.id
}

# Security Group for Ollama EC2 Instance
resource "aws_security_group" "ollama_sg" {
  name        = "${var.cluster_name}-ollama-sg"
  description = "Security group for Ollama EC2 instance"
  vpc_id      = aws_vpc.eks_vpc.id

  # Allow SSH from anywhere (you may want to restrict this to your IP)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow SSH from anywhere"
  }

  # Allow Ollama API port from anywhere
  ingress {
    from_port   = 11434
    to_port     = 11434
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow Ollama API access from anywhere"
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-ollama-sg"
    }
  )
}

# IAM Role for Ollama EC2 Instance - Use a unique name to avoid conflicts
resource "aws_iam_role" "ollama_role" {
  name = "${var.cluster_name}-ollama-role-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
  tags = var.tags
}

# IAM Instance Profile for Ollama EC2 Instance - Use a unique name to avoid conflicts
resource "aws_iam_instance_profile" "ollama_profile" {
  name = "${var.cluster_name}-ollama-profile-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  role = aws_iam_role.ollama_role.name
}

# Create a new key pair for EC2 instances
resource "tls_private_key" "ollama_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Store the private key locally so you can use it to SSH into instances
resource "local_file" "ollama_private_key" {
  content         = tls_private_key.ollama_key.private_key_pem
  filename        = "${path.module}/ollama-key.pem"
  file_permission = "0600"  # Proper permissions for SSH key
}

# Register the key pair with AWS
resource "aws_key_pair" "ollama_key_pair" {
  key_name   = "${var.cluster_name}-ollama-key"
  public_key = tls_private_key.ollama_key.public_key_openssh
}

# EC2 Instance for Ollama
resource "aws_instance" "ollama_instance" {
  ami                    = var.ollama_ami_id
  instance_type          = var.ollama_instance_type
  subnet_id              = aws_subnet.ollama_public_subnet.id
  vpc_security_group_ids = [aws_security_group.ollama_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ollama_profile.name
  associate_public_ip_address = true
  
  # Use our generated key pair
  key_name               = aws_key_pair.ollama_key_pair.key_name

  root_block_device {
    volume_size = 100
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    # Update system
    apt-get update -y
    apt-get upgrade -y

    # Install required packages
    apt-get install -y \
      ca-certificates \
      curl \
      gnupg \
      lsb-release

    # Install NVIDIA drivers and CUDA
    apt-get install -y linux-headers-$(uname -r)
    apt-get install -y nvidia-driver-535 nvidia-utils-535
    
    # Install NVIDIA container toolkit
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
      tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update
    apt-get install -y nvidia-container-toolkit

    # Install required networking tools
    apt-get install -y net-tools

    # Create Ollama configuration directory and set binding to all interfaces
    mkdir -p /etc/ollama
    cat > /etc/ollama/config << 'EOL'
    OLLAMA_HOST=0.0.0.0:11434
    EOL
    chmod 644 /etc/ollama/config

    # Install Ollama with environment variable set to listen on all interfaces
    export OLLAMA_HOST=0.0.0.0:11434
    curl -fsSL https://ollama.com/install.sh | sh

    # Verify Ollama installation
    if [ ! -f /usr/bin/ollama ]; then
      echo "Ollama installation failed. Retrying..."
      curl -fsSL https://ollama.com/install.sh | sh
    fi

    # Create a systemd override to ensure Ollama listens on all interfaces
    mkdir -p /etc/systemd/system/ollama.service.d/
    cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOL'
    [Service]
    Environment="OLLAMA_HOST=0.0.0.0:11434"
    EOL

    # Create a custom systemd service for Ollama
    cat > /etc/systemd/system/ollama-custom.service << 'EOL'
    [Unit]
    Description=Ollama API Service
    After=network-online.target
    Wants=network-online.target

    [Service]
    Environment="OLLAMA_HOST=0.0.0.0:11434"
    ExecStart=/usr/bin/ollama serve
    Restart=always
    RestartSec=3
    User=root
    LimitNOFILE=65536

    [Install]
    WantedBy=multi-user.target
    EOL

    # Reload systemd, disable default service, enable and start custom service
    systemctl daemon-reload
    systemctl disable ollama.service
    systemctl enable ollama-custom.service
    systemctl start ollama-custom.service

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
    
    # Pull the model
    echo "Pulling Ollama model: ${var.ollama_model}"
    ollama pull ${var.ollama_model}
    
    # Tag the instance to indicate setup is complete
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
    aws ec2 create-tags --resources $INSTANCE_ID --tags Key=OllamaSetupComplete,Value=true --region $REGION
  EOF

  tags = merge(
    var.tags,
    {
      Name = var.ollama_instance_name
    }
  )

  depends_on = [aws_internet_gateway.eks_igw]
}

# Security Group Rule to allow EKS nodes to communicate with Ollama instance
# This will be created after the EKS cluster is created
resource "aws_security_group_rule" "eks_to_ollama" {
  type                     = "ingress"
  from_port                = 11434
  to_port                  = 11434
  protocol                 = "tcp"
  source_security_group_id = aws_eks_cluster.eks_cluster.vpc_config[0].cluster_security_group_id
  security_group_id        = aws_security_group.ollama_sg.id
  description              = "Allow EKS cluster to access Ollama API"
  
  # This ensures the security group rule is created after the EKS cluster
  depends_on = [aws_eks_cluster.eks_cluster]
}

# Output the Ollama instance IPs
output "ollama_instance_private_ip" {
  value = aws_instance.ollama_instance.private_ip
  description = "Private IP address of the Ollama instance"
}

output "ollama_instance_public_ip" {
  value = aws_instance.ollama_instance.public_ip
  description = "Public IP address of the Ollama instance"
}

# Output instructions for connecting to Ollama from EKS
output "ollama_connection_instructions" {
  value = <<-EOT
    To connect to Ollama from your EKS pods:
    
    1. Use the following Ollama API endpoint in your applications:
       http://${aws_instance.ollama_instance.private_ip}:11434
    
    2. Example curl command from within a pod:
       curl -X POST http://${aws_instance.ollama_instance.private_ip}:11434/api/generate -d '{
         "model": "${var.ollama_model}",
         "prompt": "Hello, world!"
       }'
    
    3. To test connectivity, you can run a temporary pod:
       kubectl run curl-test --image=curlimages/curl --rm -it -- curl http://${aws_instance.ollama_instance.private_ip}:11434/api/tags
  EOT
}

# Output SSH instructions for connecting to the Ollama instance
output "ollama_ssh_instructions" {
  value = <<-EOT
    To SSH into the Ollama instance:
    
    1. The private key has been saved to: ${path.module}/ollama-key.pem
    
    2. Make sure the key has the correct permissions:
       chmod 600 ${path.module}/ollama-key.pem
    
    3. Connect using:
       ssh -i ${path.module}/ollama-key.pem ubuntu@${aws_instance.ollama_instance.public_ip}
  EOT
}

# ECR Repositories for Docker images
resource "aws_ecr_repository" "newsagent_api" {
  name                 = "newsagent-api"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = merge(
    var.tags,
    {
      Name = "newsagent-api"
    }
  )
}

resource "aws_ecr_repository" "newsagent_django" {
  name                 = "newsagent-django"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = merge(
    var.tags,
    {
      Name = "newsagent-django"
    }
  )
}

# Output ECR repository URLs
output "ecr_repository_urls" {
  value = {
    api    = aws_ecr_repository.newsagent_api.repository_url
    django = aws_ecr_repository.newsagent_django.repository_url
  }
  description = "URLs of the ECR repositories for Docker images"
}
