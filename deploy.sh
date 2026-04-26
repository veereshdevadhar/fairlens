#!/bin/bash

# FairLens Deployment Script
# Deploys Frontend to Firebase Hosting and Backend to Cloud Run

set -e

echo "🚀 Starting FairLens Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    print_error "Firebase CLI is not installed. Please install it first."
    exit 1
fi

# Backend Deployment
print_status "Deploying Backend to Cloud Run..."

cd backend

# Build and push Docker image
print_status "Building Docker image..."
gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/fairlens-backend .

# Deploy to Cloud Run
print_status "Deploying to Cloud Run..."
gcloud run deploy fairlens-backend \
    --image gcr.io/$(gcloud config get-value project)/fairlens-backend \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --port 8000 \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300s \
    --concurrency 1000 \
    --max-instances 10

# Get the Cloud Run URL
BACKEND_URL=$(gcloud run services describe fairlens-backend --region us-central1 --format 'value(status.url)')
print_status "Backend deployed to: $BACKEND_URL"

cd ..

# Frontend Deployment
print_status "Deploying Frontend to Firebase Hosting..."

cd frontend

# Install dependencies
print_status "Installing frontend dependencies..."
npm install

# Build for production
print_status "Building frontend for production..."
REACT_APP_API_URL=$BACKEND_URL npm run build

# Deploy to Firebase
print_status "Deploying to Firebase Hosting..."
firebase deploy --project fairlens-bias-detection

cd ..

print_status "🎉 Deployment completed successfully!"
print_status "Frontend: https://fairlens-bias-detection.web.app"
print_status "Backend: $BACKEND_URL"
print_warning "Don't forget to set up your GEMINI_API_KEY as a Cloud Run environment variable!"
