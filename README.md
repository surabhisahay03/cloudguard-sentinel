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

The "Senior" StackComponentToolWhy I Chose ItInfrastructureTerraform (EKS)Reproducible infrastructure with secure IAM roles (IRSA).DeploymentArgo CD (GitOps)Prevents configuration drift. The cluster state always matches Git.OrchestrationArgo WorkflowsScalable, container-native training pipelines (not just cron jobs).Model RegistryMLflowCentralized tracking for experiments and model versioning.ServingFastAPI + PollingZero-downtime model updates without restarting pods.ObservabilityPrometheus(Planned) Metrics exposed at /metrics for latency and drift monitoring.🚀 Key Features (The "Wow" Factors)1. 🛡️ Champion/Challenger Model EvaluationWe don't just deploy models; we compete them.The Logic: When a new model is trained, the pipeline automatically compares its accuracy against the current @Production model.The Safety Lock: If the new model (Challenger) is worse, the pipeline rejects the deployment.Evidence:"New model does not outperform the current production model. Not promoting." — Pipeline Logs2. 🔄 True GitOps & Self-HealingApplication deployment is decoupled from infrastructure.Argo CD constantly monitors the cluster. If a pod is deleted manually, Argo automatically heals the state.3. 🔐 Enterprise Security (No Keys!)OIDC & IRSA: This project uses AWS IAM Roles for Service Accounts.Zero Long-Lived Credentials: No AWS Access Keys are hardcoded in the application or GitHub Secrets.🛠️ How to Run This ProjectPrerequisitesAWS CLI & Terraform installed.kubectl pointing to an EKS cluster.1. Provision InfrastructureBashcd infra/eks
terraform init
terraform apply -auto-approve
2. Deploy the GitOps StackBash# Deploy Argo CD & App of Apps
kubectl apply -f infra/gitops/cloudguard-stack.yaml
3. Trigger a Training RunBash# Submit the Argo Workflow
kubectl create -f jobs/workflow.yaml
🔮 Future Roadmap (Production Readiness)If this were running in a real factory, I would add:Drift Detection: Compare live inference data in S3 against training distributions.Scalability: Enable Cluster Autoscaler to handle training spikes (currently removed monitoring stack to optimize for cost/demo constraints).A/B Testing: Use Argo Rollouts to send 5% of traffic to the new model before full promotion.
