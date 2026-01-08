# 🛡️ CloudGuard Sentinel: Industrial MLOps Platform

**CloudGuard Sentinel** is an end-to-end MLOps platform designed for **Predictive Maintenance** in manufacturing. It predicts machine failures before they happen, preventing costly downtime.

Unlike typical "notebook" projects, this is a **production-grade platform** built with **GitOps** principles, **Infrastructure as Code**, and **Automated Model Governance**.

---

## 🏗️ High-Level Architecture

```mermaid
graph LR
    subgraph "CI / CD (GitHub)"
        Dev[Developer] -->|Push Code| Repo[GitHub Repo]
        Repo -->|Trigger| Action[GitHub Actions]
        Action -->|Build & Push| Docker[GitHub Container Registry]
    end

    subgraph "The Cluster (EKS)"
        direction TB
        ArgoCD[Argo CD] -->|Sync State| Repo
        ArgoCD -->|Deploy| App[FastAPI Inference Service]
        ArgoCD -->|Deploy| Workflow[Argo Workflows]
        
        Workflow -->|1. Pull Data| S3[(S3 Data Lake)]
        Workflow -->|2. Train Model| Trainer[Training Job]
        Trainer -->|3. Log Metrics| MLflow[MLflow Registry]
        
        App -->|Load Production Model| MLflow
        App -->|Predict| EndUser[Factory Sensor API]
    end

    classDef tools fill:#f9f,stroke:#333,stroke-width:2px;
    class ArgoCD,MLflow,Workflow tools;
