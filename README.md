# 🛡️ CloudGuard Sentinel: Predictive Maintenance MLOps Platform

![CI/CD](https://github.com/surabhisahay03/cloudguard-sentinel/actions/workflows/ci.yml/badge.svg)
![Terraform](https://img.shields.io/badge/Infrastructure-Terraform-purple)
![Kubernetes](https://img.shields.io/badge/Orchestration-EKS-blue)
![GitOps](https://img.shields.io/badge/GitOps-ArgoCD-orange)

**CloudGuard Sentinel** is an end-to-end MLOps platform designed to predict industrial machine failures before they happen. It leverages a GitOps architecture to automate infrastructure, application deployment, and model training on AWS.

---

## 🏗️ Architecture
The platform follows a strict **GitOps** methodology, where the state of the infrastructure and application is defined entirely in code.

* **Infrastructure:** AWS EKS (Elastic Kubernetes Service) provisioned via **Terraform**.
* **Continuous Deployment:** **Argo CD** synchronizes Kubernetes manifests with this repository.
* **Model Training:** **Argo Workflows** orchestrates distributed training jobs on Kubernetes.
* **Model Registry:** **MLflow** tracks experiments, metrics, and manages model artifacts (stored in S3).
* **Serving:** FastAPI application serving real-time predictions (`XGBoost`).

---

## 🚀 Tech Stack

| Component | Tool | Description |
| :--- | :--- | :--- |
| **Cloud Provider** | AWS | EKS, S3, EC2, IAM, VPC |
| **IaC** | Terraform | Automates cluster & network creation |
| **Orchestration** | Kubernetes | Container management |
| **GitOps** | Argo CD | Continuous Delivery & Sync |
| **Workflow** | Argo Workflows | Training pipeline orchestration |
| **ML Platform** | MLflow | Experiment tracking & Registry |
| **Model** | XGBoost | Binary classification for failure prediction |
| **App** | FastAPI | REST API for model inference |

---

## 📂 Repository Structure

```bash
├── infra/
│   ├── eks/             # Terraform code for AWS EKS Cluster
│   └── gitops/          # Argo CD Application Manifests (The "Bridge")
├── k8s/
│   ├── charts/          # Helm Charts for App & MLflow
│   └── values/          # Environment-specific configs
├── jobs/                # Training Code & Argo Workflow definitions
├── app/                 # FastAPI Source Code
└── .github/workflows/   # CI Pipelines (Docker Build, Terraform Plan)
