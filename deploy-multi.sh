#!/bin/bash

# FairLens Multi-Platform Deployment Script
# Supports: Google Cloud Run, Render, Vercel

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Platform selection
show_help() {
    echo "FairLens Multi-Platform Deployment"
    echo ""
    echo "Usage: $0 [platform]"
    echo ""
    echo "Platforms:"
    echo "  gcloud    - Google Cloud Run (Backend)"
    echo "  render    - Render (Backend)"  
    echo "  vercel    - Vercel (Frontend)"
    echo "  all       - Deploy to all platforms"
    echo ""
    echo "Examples:"
    echo "  $0 gcloud     # Deploy backend to Google Cloud Run"
    echo "  $0 render     # Deploy backend to Render"
    echo "  $0 vercel     # Deploy frontend to Vercel"
    echo "  $0 all        # Deploy to all platforms"
}

# Deploy to Google Cloud Run
deploy_gcloud() {
    print_status "Deploying to Google Cloud Run..."
    
    cd backend
    gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/fairlens-backend .
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
    
    BACKEND_URL=$(gcloud run services describe fairlens-backend --region us-central1 --format 'value(status.url)')
    cd ..
    
    # Deploy frontend to Firebase
    print_status "Deploying frontend to Firebase..."
    cd frontend
    REACT_APP_API_URL=$BACKEND_URL npm run build
    firebase deploy --project fairlens-bias-detection
    cd ..
    
    print_status "Google Cloud deployment completed!"
    print_status "Frontend: https://fairlens-bias-detection.web.app"
    print_status "Backend: $BACKEND_URL"
}

# Deploy to Render
deploy_render() {
    print_status "Deploying to Render..."
    
    cd backend
    render deploy
    
    print_status "Render deployment completed!"
    print_status "Backend URL: https://fairlens-backend.onrender.com"
    cd ..
    
    # Deploy frontend to Vercel
    print_status "Deploying frontend to Vercel..."
    cd frontend
    npm install
    npm run build
    vercel --prod
    
    print_status "Vercel deployment completed!"
    print_status "Frontend URL: https://fairlens-frontend.vercel.app"
    cd ..
}

# Deploy to Vercel (frontend only)
deploy_vercel() {
    print_status "Deploying frontend to Vercel..."
    
    cd frontend
    npm install
    npm run build
    vercel --prod
    
    print_status "Vercel deployment completed!"
    print_status "Frontend URL: https://fairlens-frontend.vercel.app"
    cd ..
}

# Deploy to all platforms
deploy_all() {
    print_status "Deploying to all platforms..."
    
    # Backend to Google Cloud Run
    deploy_gcloud
    
    # Frontend to Vercel
    deploy_vercel
    
    print_status "Multi-platform deployment completed!"
    print_status "Frontend: https://fairlens-frontend.vercel.app"
    print_status "Backend: https://fairlens-backend-uc.a.run.app"
}

# Main script logic
case "${1:-all}" in
    gcloud)
        deploy_gcloud
        ;;
    render)
        deploy_render
        ;;
    vercel)
        deploy_vercel
        ;;
    all)
        deploy_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown platform: $1"
        show_help
        exit 1
        ;;
esac
