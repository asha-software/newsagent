# Kubernetes Deployment for NewsAgent

This directory contains Kubernetes manifests for deploying the NewsAgent application, which consists of:

1. MySQL Database (using the official mysql:8.0 image)
2. Django Web Application
3. FastAPI Application (API)

## Prerequisites

Before deploying, ensure you have:

1. A Kubernetes cluster (EKS) on AWS
2. `kubectl` installed and configured
3. AWS CLI installed and configured

## Connecting to AWS EKS

1. Configure AWS CLI with your credentials:
   ```bash
   aws configure
   ```

2. Update your kubeconfig to connect to your EKS cluster:
   ```bash
   aws eks update-kubeconfig --region <your-region> --name <your-cluster-name>
   ```

3. Verify the connection:
   ```bash
   kubectl get nodes
   ```

## Deploying the Application

The `deploy.sh` script handles all deployment steps for you:

```bash
# Build the necessary Docker images (Django and API)
./k8s/deploy.sh --build

# Deploy to Kubernetes
./k8s/deploy.sh --deploy
```

The script will:
1. Build the required Docker images
2. Create the namespace
3. Deploy all resources in the correct order
4. Wait for the database to be ready before deploying dependent services

## Accessing the Application

After deployment, check the Ingress to get the application URL:

```bash
kubectl get ingress -n newsagent
```

The ADDRESS field will contain the ALB DNS name.

## Cleanup

To remove all resources:

```bash
./k8s/deploy.sh --delete
```

## Troubleshooting

If you encounter issues:

```bash
# Check pod status
kubectl get pods -n newsagent

# View logs for a specific pod
kubectl logs <pod-name> -n newsagent

# Check all resources in the namespace
kubectl get all -n newsagent
