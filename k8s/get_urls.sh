#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print section header
print_section() {
  echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

# Print info message
print_info() {
  echo -e "${YELLOW}$1${NC}"
}

# Print error message
print_error() {
  echo -e "${RED}ERROR: $1${NC}"
  exit 1
}

print_section "Getting Application URLs"

# Check if we can connect to the Kubernetes cluster
if ! kubectl cluster-info &> /dev/null; then
  print_error "Unable to connect to Kubernetes cluster. Make sure you're connected to the right cluster."
fi

# Check ingress resources for Django
print_info "Checking ingress resources..."
if ! kubectl get ingress -n newsagent &> /dev/null; then
  print_info "No ingress resources found in the newsagent namespace."
fi

# Get LoadBalancer service information
print_info "Getting LoadBalancer service information..."

# Initialize variables
API_URL=""
DJANGO_URL=""

# Get API LoadBalancer hostname or IP
API_HOSTNAME=$(kubectl get svc newsagent-api -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
if [ -n "$API_HOSTNAME" ]; then
  API_URL="http://${API_HOSTNAME}:8001"
  print_info "API LoadBalancer hostname: $API_HOSTNAME"
else
  # Try to get IP (some cloud providers return IP instead of hostname)
  API_IP=$(kubectl get svc newsagent-api -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
  if [ -n "$API_IP" ]; then
    API_URL="http://${API_IP}:8001"
    print_info "API LoadBalancer IP: $API_IP"
  else
    print_info "API LoadBalancer hostname/IP not found."
    API_URL="URL not found"
  fi
fi

# Get Django LoadBalancer hostname or IP
DJANGO_HOSTNAME=$(kubectl get svc newsagent-django -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
if [ -n "$DJANGO_HOSTNAME" ]; then
  DJANGO_URL="http://${DJANGO_HOSTNAME}:8000"
  print_info "Django LoadBalancer hostname: $DJANGO_HOSTNAME"
else
  # Try to get IP (some cloud providers return IP instead of hostname)
  DJANGO_IP=$(kubectl get svc newsagent-django -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
  if [ -n "$DJANGO_IP" ]; then
    DJANGO_URL="http://${DJANGO_IP}:8000"
    print_info "Django LoadBalancer IP: $DJANGO_IP"
  else
    print_info "Django LoadBalancer hostname/IP not found."
    DJANGO_URL="URL not found"
  fi
fi

# Update the configmap with the internal service names
print_info "Updating configmap with internal service names..."
kubectl patch configmap newsagent-config -n newsagent --type=merge -p '{"data":{"API_SERVICE_URL":"http://newsagent-api.newsagent.svc.cluster.local:8000","OLLAMA_SERVICE_URL":"http://newsagent-ollama.newsagent.svc.cluster.local:11434"}}'

# Make sure the API deployment has the API_SERVICE_URL environment variable
print_info "Ensuring API deployment has the API_SERVICE_URL environment variable..."
kubectl patch deployment newsagent-api -n newsagent --type=json -p '[{"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"API_SERVICE_URL","valueFrom":{"configMapKeyRef":{"key":"API_SERVICE_URL","name":"newsagent-config"}}}}]' || true

# Override the OLLAMA_BASE_URL environment variable
print_info "Overriding OLLAMA_BASE_URL environment variable..."
kubectl patch deployment newsagent-api -n newsagent --type=json -p '[{"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"OLLAMA_BASE_URL","value":"http://newsagent-ollama.newsagent.svc.cluster.local:11434"}}]' || true

# Restart the API deployment to pick up the new configmap values
print_info "Restarting API deployment to pick up the new configmap values..."
kubectl rollout restart deployment/newsagent-api -n newsagent

# Wait for the API deployment to be ready
print_info "Waiting for API deployment to be ready..."
kubectl rollout status deployment/newsagent-api -n newsagent

# Restart the Django deployment to pick up the new environment variable
print_info "Restarting Django deployment to pick up the new environment variable..."
kubectl rollout restart deployment/newsagent-django -n newsagent

# Wait for the Django deployment to be ready
print_info "Waiting for Django deployment to be ready..."
kubectl rollout status deployment/newsagent-django -n newsagent

# Display URLs
echo -e "\n${GREEN}Application URLs:${NC}"
echo -e "${YELLOW}Django Application:${NC} $DJANGO_URL"
echo -e "${YELLOW}API Endpoint:${NC} $API_URL/api"

# Get pod status
echo -e "\n${YELLOW}Pod Status:${NC}"
kubectl get pods -n newsagent

# Get service status
echo -e "\n${YELLOW}Service Status:${NC}"
kubectl get svc -n newsagent
