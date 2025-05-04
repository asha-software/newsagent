output "cluster_id" {
  description = "EKS cluster ID"
  value       = aws_eks_cluster.eks_cluster.id
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = aws_eks_cluster.eks_cluster.endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = aws_security_group.eks_cluster_sg.id
}

output "cluster_name" {
  description = "Kubernetes Cluster Name"
  value       = aws_eks_cluster.eks_cluster.name
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.eks_cluster.certificate_authority[0].data
}

output "ecr_repository_urls" {
  description = "URLs of the created ECR repositories"
  value       = [for repo in aws_ecr_repository.ecr_repos : repo.repository_url]
}

output "kubeconfig_command" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.eks_cluster.name}"
}

output "node_group_id" {
  description = "EKS node group ID"
  value       = aws_eks_node_group.gpu_node_group.id
}

output "node_group_status" {
  description = "EKS node group status"
  value       = aws_eks_node_group.gpu_node_group.status
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.eks_vpc.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "ssh_key_path" {
  description = "Path to the SSH private key for node access"
  value       = local_file.eks_private_key.filename
}

output "ssh_key_name" {
  description = "Name of the SSH key pair in AWS"
  value       = aws_key_pair.eks_key.key_name
}
