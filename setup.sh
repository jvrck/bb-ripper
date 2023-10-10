#!/usr/bin/env bash
set -ex

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
    echo Argument not provided ; 
fi
