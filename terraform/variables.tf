# AWS Region
variable "aws_region" {
  description = "The AWS region to deploy resources in"
  type        = string
  default     = "us-west-2"
}

# Kubernetes Version
variable "kubernetes_version" {
  description = "Kubernetes version to use for the EKS cluster"
  type        = string
  default     = "1.32"
}

# Cluster Configuration
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "newsagent-cluster"
}

variable "endpoint_private_access" {
  description = "Whether to enable private access to the cluster's API server endpoint"
  type        = bool
  default     = true
}

variable "endpoint_public_access" {
  description = "Whether to enable public access to the cluster's API server endpoint"
  type        = bool
  default     = true
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# Node Group Configuration
variable "node_instance_type" {
  description = "EC2 instance type for the node group"
  type        = string
  default     = "t3.medium"
}

variable "node_desired_size" {
  description = "Desired number of nodes in the node group"
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum number of nodes in the node group"
  type        = number
  default     = 3
}

variable "node_min_size" {
  description = "Minimum number of nodes in the node group"
  type        = number
  default     = 1
}

# SSH Access Configuration (Optional)
variable "ssh_key_name" {
  description = "EC2 Key Pair name for SSH access to the nodes (optional)"
  type        = string
  default     = null
}

variable "source_security_group_ids" {
  description = "List of security group IDs that are allowed SSH access to the nodes (optional)"
  type        = list(string)
  default     = []
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {
    Environment = "dev"
    Project     = "newsagent"
    ManagedBy   = "terraform"
  }
}

# Ollama EC2 Instance Configuration
variable "ollama_ami_id" {
  description = "AMI ID for the Ollama EC2 instance (Ubuntu 22.04 recommended)"
  type        = string
  default     = "ami-0c65adc9a5c1b5d7c" # Ubuntu 22.04 LTS in us-west-2, update for your region
}

variable "ollama_model" {
  description = "Ollama model to run"
  type        = string
  default     = "mistral-nemo"
}

variable "ollama_instance_name" {
  description = "Name for the Ollama EC2 instance"
  type        = string
  default     = "ollama-gpu-instance"
}

variable "ollama_instance_type" {
  description = "EC2 instance type for the Ollama instance"
  type        = string
  default     = "g4dn.xlarge"
}
