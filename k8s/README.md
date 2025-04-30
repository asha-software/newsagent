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

After deployment, the `deploy.sh` script will automatically display the URLs for accessing your application:

```
============================================================
                   ACCESS INFORMATION                       
============================================================
Your application is now accessible at the following URLs:

Django Frontend: http://<DJANGO-HOSTNAME>:8000
API Endpoint: http://<API-HOSTNAME>:8001
API Documentation: http://<API-HOSTNAME>:8001/docs
============================================================
```

The script will wait for the load balancers to be provisioned and display these URLs automatically. If for some reason the URLs are not displayed, you can manually check them with:

```bash
# Get the external hostnames for the Django and API services
kubectl get services -n newsagent
```

Look for the `EXTERNAL-IP` column in the output. You'll see external hostnames for both the Django and API services:

- Django frontend: `http://<DJANGO-EXTERNAL-IP>:8000`
- API endpoint: `http://<API-EXTERNAL-IP>:8001`
- API documentation: `http://<API-EXTERNAL-IP>:8001/docs`

It may take a few minutes for the Load Balancers to be provisioned and for DNS to propagate. If you can't access the URLs immediately, wait a few minutes and try again.

For class demonstrations, you can share these URLs with your audience to access the application.

### Quick URL Check

If you need to quickly check the URLs after deployment, you can use the provided script:

```bash
./k8s/get_urls.sh
```

This script will display the current URLs for the Django frontend and API endpoints, as well as the current status of all services.

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
