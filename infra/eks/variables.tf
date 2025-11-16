# --- AWS Provider ---
variable "aws_region" {
  description = "The AWS region to deploy to."
  type        = string
  default     = "us-east-1" # <-- The default value
}

# --- EKS Cluster ---
variable "cluster_name" {
  description = "The name for the EKS cluster."
  type        = string
  default     = "cloudguard-eks" # <-- The default value
}

variable "cluster_version" {
  description = "The Kubernetes version for the EKS cluster."
  type        = string
  default     = "1.30" # <-- The default value
}

variable "availability_zones" {
  description = "A list of availability zones to use for the cluster."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"] # <-- The default value
}

variable "cluster_endpoint_public_access" {
  description = "Enable public access to the cluster's API endpoint."
  type        = bool
  default     = true # <-- The default value
}

variable "cluster_endpoint_private_access" {
  description = "Enable private access to the cluster's API endpoint."
  type        = bool
  default     = false # <-- The default value
}

# --- EKS Access ---
variable "cluster_admin_arn" {
  description = "The ARN of the IAM principal to grant admin access."
  type        = string
  sensitive   = true
  # <-- NO DEFAULT. This is correct, as it's injected from secrets.
}

# --- EKS Node Group ---
variable "eks_node_instance_type" {
  description = "The EC2 instance type for the EKS nodes."
  type        = string
  default     = "t3.medium" # <-- The default value
}

variable "eks_node_min_size" {
  description = "The minimum number of nodes for the node group."
  type        = number
  default     = 2 # <-- The default value
}

variable "eks_node_max_size" {
  description = "The maximum number of nodes for the node group."
  type        = number
  default     = 4 # <-- The default value
}

variable "eks_node_desired_size" {
  description = "The desired number of nodes for the node group."
  type        = number
  default     = 2 # <-- The default value
}
