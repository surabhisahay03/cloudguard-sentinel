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

data "aws_subnets" "control_plane"{
  filter {
    name = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name = "availability-zone"
    values = ["us-east-1a", "us-east-1b"]
  }
}


# --- NEW DATA BLOCK FOR IRSA POLICY ---
# This policy says: "You are allowed to 'PutObject' (upload)
# into our new log bucket, and only that bucket."
data "aws_iam_policy_document" "app_pod_s3_policy_doc" {
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",          # Allow writing models
      "s3:GetObject",          # Allow reading models (for deployment)
      "s3:ListBucket",         # Allow checking if the folder exists (Fixes your error!)
      "s3:GetBucketLocation",  # Helper for region detection
      "s3:DeleteObject"        # Allow deleting experiments from UI
    ]
    resources = [
      # Keep BOTH of these lines.
      # Line 1 allows "ListBucket" (on the bucket itself)
      aws_s3_bucket.prediction_logs.arn,

      # Line 2 allows "Put/Get/Delete" (on the files inside)
      "${aws_s3_bucket.prediction_logs.arn}/*"
    ]
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
  control_plane_subnet_ids = data.aws_subnets.control_plane.ids

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

      capacity_type = "SPOT"

      # This is a better, more flexible way to size your nodes
      min_size     = var.eks_node_min_size
      max_size     = var.eks_node_max_size
      desired_size = var.eks_node_desired_size
    }
  }
}


# --- S3 Bucket for ML Prediction Logs ---
# (This is our new resource, placed after the EKS module in Section 3)
resource "aws_s3_bucket" "prediction_logs" {
  # We get the bucket name from a variable to keep it flexible
  bucket = var.prediction_log_bucket_name

  # Prevents the S3 bucket from being accidentally deleted
  # by 'terraform destroy'. We'll have to manually empty
  # and delete it, which is safer for production data.
  lifecycle {
    prevent_destroy = true
  }
}

# Enforce security best practices:
# 1. Block all public access
# 2. Enable server-side encryption by default
resource "aws_s3_bucket_public_access_block" "prediction_logs_pac" {
  bucket = aws_s3_bucket.prediction_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "prediction_logs_sse" {
  bucket = aws_s3_bucket.prediction_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}


# --- IAM Role for Service Account (IRSA) ---
resource "aws_iam_role" "app_pod_role" {
  name = "cloudguard-app-pod-role"

  # TRUST POLICY FIX: We updated this to allow a LIST of Service Accounts.
  # This acts as the "Bouncer" letting two different VIPs into the club.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = module.eks.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            # Note the square brackets [] below. This allows multiple Service Accounts.
            "${module.eks.oidc_provider}:sub" = [
              "system:serviceaccount:default:cloudguard-sa",              # 1. The FastAPI App
              "system:serviceaccount:argo:workflow-runner",               # 2. The Argo Workflow (Trainer)
              "system:serviceaccount:mlflow:mlflow-server"
            ]
          }
        }
      }
    ]
  })
}

# 3. Attach the S3 Policy to the IAM Role
resource "aws_iam_role_policy" "app_pod_s3_policy" {
  name   = "s3-log-writer-policy"
  role   = aws_iam_role.app_pod_role.name
  policy = data.aws_iam_policy_document.app_pod_s3_policy_doc.json
}
