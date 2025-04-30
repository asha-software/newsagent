#!/bin/bash

# Script to get the URLs for the Django and API services

# Check if the namespace exists
if ! kubectl get namespace newsagent &>/dev/null; then
  echo "Error: The 'newsagent' namespace does not exist. Please deploy the application first."
  exit 1
fi

# Check if the services exist
if ! kubectl get service django -n newsagent &>/dev/null; then
  echo "Error: The 'django' service does not exist. Please deploy the application first."
  exit 1
fi

if ! kubectl get service api -n newsagent &>/dev/null; then
  echo "Error: The 'api' service does not exist. Please deploy the application first."
  exit 1
fi

# Get and display the URLs
echo ""
echo "============================================================"
echo "                   ACCESS INFORMATION                       "
echo "============================================================"
echo "Your application is accessible at the following URLs:"
echo ""

# Get Django URL
DJANGO_HOSTNAME=$(kubectl get service django -n newsagent --template="{{range .status.loadBalancer.ingress}}{{.hostname}}{{end}}")
if [ -n "$DJANGO_HOSTNAME" ]; then
  echo "Django Frontend: http://$DJANGO_HOSTNAME:8000"
else
  echo "Django Frontend: URL not available yet. The load balancer may still be provisioning."
  echo "Run 'kubectl get service django -n newsagent' to check status."
fi

# Get API URL
API_HOSTNAME=$(kubectl get service api -n newsagent --template="{{range .status.loadBalancer.ingress}}{{.hostname}}{{end}}")
if [ -n "$API_HOSTNAME" ]; then
  echo "API Endpoint: http://$API_HOSTNAME:8001"
  echo "API Documentation: http://$API_HOSTNAME:8001/docs"
else
  echo "API Endpoint: URL not available yet. The load balancer may still be provisioning."
  echo "Run 'kubectl get service api -n newsagent' to check status."
fi

echo "============================================================"
echo "Note: It may take a few minutes for DNS to propagate and for the services to be fully accessible."
echo ""

# Display the current status of the services
echo "Current status of services:"
kubectl get services -n newsagent
