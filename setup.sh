#!/usr/bin/env bash
set -ex

# Update apt and install git
apt-get update && apt-get upgrade -y && apt-get install -y git

# Install AWS CLI 
if [ "$AWSCLI" == "TRUE" ] ; then 
    # Required for AWS CLI download and unzip. Remove after installation.
    apt-get install -y curl unzip ;
    
    # Download and install AWS CLI. Clean up after installation.
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" ;
    unzip awscliv2.zip ;
    ./aws/install ;
    rm -rf aws ;
    rm -rf awscliv2.zip ;

    # Clean up after installation.  
    apt-get -y --purge remove curl unzip ;
else 
    echo AWSCLI argument not provided ; 
fi

# Clean up apt cache
apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
