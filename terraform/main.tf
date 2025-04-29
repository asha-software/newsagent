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

# Private Subnet for Ollama EC2 Instance
resource "aws_subnet" "ollama_private_subnet" {
  vpc_id                  = aws_vpc.eks_vpc.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 10) # Using a different subnet range
  map_public_ip_on_launch = false
  availability_zone       = data.aws_availability_zones.available.names[0]
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-ollama-private-subnet"
    }
  )
}

# NAT Gateway for Private Subnet Internet Access
resource "aws_eip" "nat_eip" {
  domain = "vpc"
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-nat-eip"
    }
  )
}

resource "aws_nat_gateway" "nat_gateway" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.eks_public_subnet[0].id
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-nat-gateway"
    }
  )
  depends_on = [aws_internet_gateway.eks_igw]
}

# Route Table for Private Subnet
resource "aws_route_table" "ollama_private_rt" {
  vpc_id = aws_vpc.eks_vpc.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gateway.id
  }
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-ollama-private-rt"
    }
  )
}

# Route Table Association for Private Subnet
resource "aws_route_table_association" "ollama_private_rt_assoc" {
  subnet_id      = aws_subnet.ollama_private_subnet.id
  route_table_id = aws_route_table.ollama_private_rt.id
}

# Security Group for Ollama EC2 Instance
resource "aws_security_group" "ollama_sg" {
  name        = "${var.cluster_name}-ollama-sg"
  description = "Security group for Ollama EC2 instance"
  vpc_id      = aws_vpc.eks_vpc.id

  # Allow SSH from within VPC
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Allow SSH from within VPC"
  }

  # Allow Ollama API port from within VPC
  ingress {
    from_port   = 11434
    to_port     = 11434
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Allow Ollama API access from within VPC"
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
  subnet_id              = aws_subnet.ollama_private_subnet.id
  vpc_security_group_ids = [aws_security_group.ollama_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ollama_profile.name
  
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

    # Install Ollama
    curl -fsSL https://ollama.com/install.sh | sh

    # Pull and run the Ollama model
    systemctl enable ollama
    systemctl start ollama
    
    # Wait for Ollama service to start
    sleep 10
    
    # Pull the model
    ollama pull ${var.ollama_model}
    
    # Create a systemd service to ensure Ollama starts on boot
    cat > /etc/systemd/system/ollama-model.service << 'EOL'
    [Unit]
    Description=Ollama Model Service
    After=ollama.service
    Requires=ollama.service

    [Service]
    Type=simple
    User=root
    ExecStart=/usr/bin/ollama serve
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
    EOL

    systemctl daemon-reload
    systemctl enable ollama-model.service
    systemctl start ollama-model.service
    
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

  depends_on = [aws_nat_gateway.nat_gateway]
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

# Output the Ollama instance private IP
output "ollama_instance_private_ip" {
  value = aws_instance.ollama_instance.private_ip
  description = "Private IP address of the Ollama instance"
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
       ssh -i ${path.module}/ollama-key.pem ubuntu@${aws_instance.ollama_instance.private_ip}
       
    Note: Since the instance is in a private subnet, you'll need to connect through a bastion host or VPN.
  EOT
}
