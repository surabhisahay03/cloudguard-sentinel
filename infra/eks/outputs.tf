output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --region us-east-1 --name cloudguard-eks"
  description = "Run this to connect kubectl to the new cluster"
}

output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint URL of the EKS cluster"
  value       = module.eks.cluster_endpoint
}
