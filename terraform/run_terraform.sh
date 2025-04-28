#!/bin/bash

# Load environment variables from core/.env
if [ -f "../core/.env" ]; then
    echo "Loading AWS credentials from core/.env"
    export $(grep -v '^#' ../core/.env | xargs)
else
    echo "Error: core/.env file not found"
    exit 1
fi

# Check if AWS credentials are loaded
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "Error: AWS credentials not found in core/.env"
    echo "Please make sure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set in core/.env"
    exit 1
fi

echo "AWS credentials loaded successfully"
echo "Using AWS region: $AWS_REGION"

# Run the terraform command with the simplified configuration files
if [ $# -eq 0 ]; then
    echo "Usage: ./run_simplified_terraform.sh [terraform command]"
    echo "Example: ./run_simplified_terraform.sh init"
    echo "Example: ./run_simplified_terraform.sh plan"
    echo "Example: ./run_simplified_terraform.sh apply"
    exit 1
fi

# Create a temporary directory for the simplified configuration
TEMP_DIR="simplified_terraform_tmp"
mkdir -p $TEMP_DIR

# Copy the simplified configuration files to the temporary directory
cp simplified_main.tf $TEMP_DIR/main.tf
cp simplified_variables.tf $TEMP_DIR/variables.tf

echo "Running: terraform -chdir=$TEMP_DIR $@"
terraform -chdir=$TEMP_DIR "$@"

# Cleanup temporary directory if the command was successful
if [ $? -eq 0 ] && [ "$1" != "init" ]; then
    echo "Cleaning up temporary directory..."
    # Don't remove the directory if it was just initialized, as we'll need it for subsequent commands
    # rm -rf $TEMP_DIR
fi
