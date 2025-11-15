terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.60" }
  }

  backend "s3" {
    bucket         = "tfstate-surabhisahay03-cloudguard"
    key            = "eks/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "tf-locks-cloudguard"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

# Use default VPC & subnets
data "aws_vpc" "default" { default = true }

# # Get all subnet IDs in that VPC (v5 syntax)
# data "aws_subnets" "default" {
#   filter {
#     name   = "vpc-id"
#     values = [data.aws_vpc.default.id]
#   }
# }

# Only subnets in supported AZs (exclude 1e)
data "aws_subnets" "eks_supported" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "availability-zone"
    values = ["us-east-1a", "us-east-1b"]  # <-- adjust if needed
  }
}

# EKS module: creates the cluster + a small node group
module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "~> 20.2"

  cluster_name    = "cloudguard-eks"
  cluster_version = "1.30"

  vpc_id     = data.aws_vpc.default.id
  subnet_ids               = data.aws_subnets.eks_supported.ids
  control_plane_subnet_ids = data.aws_subnets.eks_supported.ids  # explicit & safe

  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = false

    # --- Grant your IAM user cluster-admin automatically ---
  access_entries = {
    admin = {
      principal_arn = "arn:aws:iam::447646782725:user/terraform-admin"
      policy_associations = {
        admin = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }
  }

  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.medium"]
      desired_size   = 1
      max_size       = 1
      min_size       = 1
    }
  }
}
