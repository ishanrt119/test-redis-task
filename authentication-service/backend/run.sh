#!/bin/bash

PORT=$1

if [ -z "$PORT" ]; then
    echo "Usage: ./run.sh <port>"
    exit 1
fi

export SERVICE_PORT=$PORT

python3 manage.py runserver $PORT --noreload