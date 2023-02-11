#!/usr/bin/env bash
set -ex

# Install AWS CLI 
if [ "$AWSCLI" == "TRUE" ] ; then 
    pip3 install awscli ; 
else 
    echo Argument not provided ; 
fi