# AWS Region
aws_region = "us-east-1"

# Kubernetes Version
kubernetes_version = "1.32"

# Cluster Configuration
cluster_name = "newsagent-clusterv2"
endpoint_private_access = true
endpoint_public_access = true

# VPC Configuration
vpc_cidr = "10.0.0.0/16"

# Node Group Configuration
node_instance_type = "t3.medium"
node_desired_size = 1
node_max_size = 3
node_min_size = 1

# SSH Access Configuration
# Uncomment and set these values if you want to use SSH access
ssh_key_name = "ollama-key"  # Using the key that was created in the AWS console
# source_security_group_ids = ["sg-12345678"]

# Ollama EC2 Instance Configuration
ollama_ami_id = "ami-00ca0754cabb20b45" # Ubuntu 22.04 LTS in us-east-1, update for your region
ollama_model = "mistral-nemo"
ollama_instance_name = "ollama-gpu-instance"
ollama_instance_type = "g4dn.xlarge"  # You can change this to another GPU instance type if needed
