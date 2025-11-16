# --- 1. CONFIGURATION ---
terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.60" }
  }

  backend "s3" {
    # These values are for the backend and must be hardcoded here
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

# --- 2. DATA LOOKUPS (The "Read" step) ---
data "aws_vpc" "default" { default = true }

data "aws_subnets" "eks_supported" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "availability-zone"
    values = var.availability_zones
  }
}

# --- 3. THE RESOURCES (The "Write" step) ---
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.2"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id                   = data.aws_vpc.default.id
  subnet_ids               = data.aws_subnets.eks_supported.ids
  control_plane_subnet_ids = data.aws_subnets.eks_supported.ids

  cluster_endpoint_public_access  = var.cluster_endpoint_public_access
  cluster_endpoint_private_access = var.cluster_endpoint_private_access

  # --- Grant your IAM user cluster-admin automatically ---
  access_entries = {
    admin = {
      principal_arn = var.cluster_admin_arn # <-- Already a variable (good!)
      policy_associations = {
        admin = {
          # This ARN is a fixed AWS policy, so it's fine to leave hardcoded
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }
  }

  eks_managed_node_groups = {
    default = {
      instance_types = [var.eks_node_instance_type] # <-- Already a variable (good!)

      # This is a better, more flexible way to size your nodes
      min_size     = var.eks_node_min_size
      max_size     = var.eks_node_max_size
      desired_size = var.eks_node_desired_size
    }
  }
}
