output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
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

output "app_pod_role_arn" {
  description = "The ARN of the IAM role for the app pods."
  value       = aws_iam_role.app_pod_role.arn
}
