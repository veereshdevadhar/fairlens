# 🚀 FairLens Deployment Guide

## **Architecture Overview**
- **Frontend**: Firebase Hosting (static React app)
- **Backend**: Cloud Run (containerized FastAPI)
- **Database**: In-memory (datasets loaded at startup)
- **AI**: Google Gemini API (optional)

## **Prerequisites**

### **Google Cloud Setup**
1. Create Google Cloud Project: [console.cloud.google.com](https://console.cloud.google.com)
2. Enable APIs:
   - Cloud Run API
   - Cloud Build API
   - Container Registry API
3. Install gcloud CLI:
   ```bash
   curl https://sdk.cloud.google.com | bash
   gcloud init
   ```

### **Firebase Setup**
1. Create Firebase Project: [console.firebase.google.com](https://console.firebase.google.com)
2. Install Firebase CLI:
   ```bash
   npm install -g firebase-tools
   firebase login
   ```

### **Environment Variables**
```bash
# Set your Gemini API key (optional)
gcloud run services update fairlens-backend \
  --region us-central1 \
  --set-env-vars GEMINI_API_KEY=your_key_here
```

## **🔧 Quick Deployment**

### **Option 1: Automated Deployment**
```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### **Option 2: Manual Deployment**

#### **Backend - Cloud Run**
```bash
cd backend

# Build and push Docker image
gcloud builds submit --tag gcr.io/PROJECT_ID/fairlens-backend .

# Deploy to Cloud Run
gcloud run deploy fairlens-backend \
  --image gcr.io/PROJECT_ID/fairlens-backend \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000
```

#### **Frontend - Firebase Hosting**
```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Deploy to Firebase
firebase deploy
```

## **🌐 Access URLs**
- **Frontend**: https://fairlens-bias-detection.web.app
- **Backend**: https://fairlens-backend-uc.a.run.app
- **API Docs**: https://fairlens-backend-uc.a.run.app/docs

## **🔧 Configuration**

### **Frontend Environment Variables**
Create `.env` in frontend directory:
```env
REACT_APP_API_URL=https://fairlens-backend-uc.a.run.app
```

### **Backend Environment Variables**
Set via Cloud Run:
```bash
gcloud run services update fairlens-backend \
  --region us-central1 \
  --set-env-vars GEMINI_API_KEY=your_key_here
```

## **📊 Monitoring & Scaling**

### **Cloud Run Monitoring**
- **Console**: Cloud Run → Services → fairlens-backend
- **Metrics**: Request count, latency, error rates
- **Logs**: Cloud Logging for debugging

### **Firebase Hosting**
- **Console**: Firebase Hosting → Hosting
- **Analytics**: Built-in usage analytics
- **Custom Domain**: Add custom domain in Firebase console

### **Auto-scaling Configuration**
```yaml
# In cloudbuild.yaml
--memory=1Gi          # Memory per instance
--cpu=1               # CPU per instance  
--concurrency=1000    # Max concurrent requests
--max-instances=10    # Max instances
--timeout=300s        # Request timeout
```

## **🛠️ Troubleshooting**

### **Common Issues**

#### **Backend Not Responding**
```bash
# Check logs
gcloud logs read "resource.type=cloud_run_revision"

# Check service status
gcloud run services describe fairlens-backend --region us-central1
```

#### **Frontend API Errors**
- Check CORS settings in backend
- Verify API URL in frontend `.env`
- Check Cloud Run service is running

#### **High Memory Usage**
- Increase memory allocation:
```bash
gcloud run services update fairlens-backend \
  --region us-central1 \
  --memory 2Gi
```

### **Performance Optimization**

#### **Backend Caching**
```python
# Add to main.py
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

FastAPICache.init(InMemoryBackend())
```

#### **Frontend Optimization**
```bash
# Build with optimization
npm run build

# Analyze bundle size
npm run analyze
```

## **🔒 Security**

### **API Security**
- Cloud Run IAM permissions
- API rate limiting
- Input validation
- HTTPS enforced

### **Firebase Security**
- Firebase security rules
- Custom SSL certificates
- Domain verification

## **💰 Cost Estimation**

### **Cloud Run** (Free Tier: 2M requests/month)
- **Requests**: $0.40 per million
- **CPU**: $0.000024 per vCPU-second  
- **Memory**: $0.0000025 per GB-second
- **Network**: $0.12 per GB

### **Firebase Hosting** (Free Tier: 10GB storage)
- **Storage**: $0.026 per GB-month
- **Bandwidth**: Free up to 10GB/month

**Estimated Monthly Cost**: $5-20 for moderate usage

## **🚀 Production Checklist**

- [ ] Set up custom domain
- [ ] Configure SSL certificates  
- [ ] Set up monitoring alerts
- [ ] Configure backup strategy
- [ ] Test disaster recovery
- [ ] Set up CI/CD pipeline
- [ ] Document API endpoints
- [ ] Performance testing
- [ ] Security audit
- [ ] User acceptance testing

## **📞 Support**

- **Google Cloud Support**: [cloud.google.com/support](https://cloud.google.com/support)
- **Firebase Support**: [firebase.google.com/support](https://firebase.google.com/support)
- **Documentation**: [github.com/veereshdevadhar/fairlens](https://github.com/veereshdevadhar/fairlens)
