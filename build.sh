#!/usr/bin/env bash

# script for building python binary using a debian docker container environment
# interestingly, there can compatibility issues even when creating a python binary

set -e

CONTAINER_NAME="dum"
IMAGE_NAME="${CONTAINER_NAME}_image"
BUILD_CONTEXT="."
MAIN_SCRIPT="src/main.py"
OUTPUT_DIR="$(pwd)/${CONTAINER_NAME}"
VENV_PATH="/app/venv/bin/pyinstaller"
PYINSTALLER_OPTIONS="--onefile"

if docker images -a | grep -q "$IMAGE_NAME"; then
    docker rmi "$IMAGE_NAME"
fi

docker build -t $IMAGE_NAME $BUILD_CONTEXT

docker run --rm --name $CONTAINER_NAME \
    -v "$OUTPUT_DIR:/app/dist" \
    $IMAGE_NAME \
    $VENV_PATH $PYINSTALLER_OPTIONS $MAIN_SCRIPT --name $CONTAINER_NAME
