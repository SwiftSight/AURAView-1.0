#!/bin/bash

# Install Python dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies
cd frontend
npm install

echo "Environment setup complete."
