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

# Get ingress resources
print_info "Checking ingress resources..."
if ! kubectl get ingress -n newsagent &> /dev/null; then
  print_error "No ingress resources found in the newsagent namespace."
fi

# First try to get service information (LoadBalancer type)
print_info "Getting service information..."
DJANGO_INGRESS=$(kubectl get svc newsagent-django -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
API_INGRESS=$(kubectl get svc newsagent-api -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)

# If service information is not available, try ingress resources
if [ -z "$DJANGO_INGRESS" ] || [ -z "$API_INGRESS" ]; then
  print_info "Service hostnames not found. Trying to get ingress information..."
  
  # Try to get ingress information
  DJANGO_INGRESS_HOST=$(kubectl get ingress newsagent-django-ingress -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
  API_INGRESS_HOST=$(kubectl get ingress newsagent-api-ingress -n newsagent -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
  
  if [ -n "$DJANGO_INGRESS_HOST" ]; then
    DJANGO_INGRESS=$DJANGO_INGRESS_HOST
  fi
  
  if [ -n "$API_INGRESS_HOST" ]; then
    API_INGRESS=$API_INGRESS_HOST
  fi
fi

# Get ALB information from AWS CLI if still not found
if [ -z "$DJANGO_INGRESS" ] || [ -z "$API_INGRESS" ]; then
  print_info "Trying to get ALB information from AWS CLI..."
  
  # Get all load balancers
  LBS=$(aws elbv2 describe-load-balancers --query 'LoadBalancers[*].{DNSName:DNSName,LoadBalancerArn:LoadBalancerArn}' --output json)
  
  # Get all target groups
  TGS=$(aws elbv2 describe-target-groups --query 'TargetGroups[*].{TargetGroupArn:TargetGroupArn,LoadBalancerArns:LoadBalancerArns}' --output json)
  
  # Find target groups associated with our services
  DJANGO_TG=$(kubectl get ingress newsagent-django-ingress -n newsagent -o jsonpath='{.metadata.annotations.alb\.ingress\.kubernetes\.io/target-group-arn}' 2>/dev/null)
  API_TG=$(kubectl get ingress newsagent-api-ingress -n newsagent -o jsonpath='{.metadata.annotations.alb\.ingress\.kubernetes\.io/target-group-arn}' 2>/dev/null)
  
  # If we found target groups, find the associated load balancers
  if [ -n "$DJANGO_TG" ]; then
    DJANGO_LB=$(echo $TGS | jq -r --arg tg "$DJANGO_TG" '.[] | select(.TargetGroupArn==$tg) | .LoadBalancerArns[0]')
    if [ -n "$DJANGO_LB" ]; then
      DJANGO_INGRESS=$(echo $LBS | jq -r --arg lb "$DJANGO_LB" '.[] | select(.LoadBalancerArn==$lb) | .DNSName')
    fi
  fi
  
  if [ -n "$API_TG" ]; then
    API_LB=$(echo $TGS | jq -r --arg tg "$API_TG" '.[] | select(.TargetGroupArn==$tg) | .LoadBalancerArns[0]')
    if [ -n "$API_LB" ]; then
      API_INGRESS=$(echo $LBS | jq -r --arg lb "$API_LB" '.[] | select(.LoadBalancerArn==$lb) | .DNSName')
    fi
  fi
fi

# Display URLs
echo -e "\n${GREEN}Application URLs:${NC}"
if [ -n "$DJANGO_INGRESS" ]; then
  echo -e "${YELLOW}Django Application:${NC} http://$DJANGO_INGRESS:8000"
else
  echo -e "${YELLOW}Django Application:${NC} URL not found"
fi

if [ -n "$API_INGRESS" ]; then
  echo -e "${YELLOW}API Endpoint:${NC} http://$API_INGRESS:8000/api"
else
  echo -e "${YELLOW}API Endpoint:${NC} URL not found"
fi

# Get pod status
echo -e "\n${YELLOW}Pod Status:${NC}"
kubectl get pods -n newsagent
