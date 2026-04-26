@echo off
REM FairLens Windows Deployment Script
REM Supports: Google Cloud Run, Render, Vercel

setlocal enabledelayedexpansion

REM Colors for output
set "GREEN=[32m"
set "YELLOW=[33m"  
set "RED=[31m"
set "NC=[0m"

:print_status
echo %GREEN%[INFO]%NC% %~1
goto :eof

:print_warning
echo %YELLOW%[WARNING]%NC% %~1
goto :eof

:print_error
echo %RED%[ERROR]%NC% %~1
goto :eof

REM Display help
if "%1"=="--help" goto :help
if "%1"=="-h" goto :help

REM Check if required tools are available
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    call :print_error "Google Cloud CLI (gcloud) not found. Please install it first."
    goto :eof
)

where firebase >nul 2>nul
if %errorlevel% neq 0 (
    call :print_error "Firebase CLI (firebase) not found. Please install it first."
    goto :eof
)

REM Platform selection
if "%1"=="gcloud" goto :deploy_gcloud
if "%1"=="render" goto :deploy_render
if "%1"=="vercel" goto :deploy_vercel
if "%1"=="all" goto :deploy_all
goto :help

:deploy_gcloud
call :print_status "Deploying to Google Cloud Run..."
cd backend
gcloud builds submit --tag gcr.io/%%PROJECT_ID%%/fairlens-backend .
gcloud run deploy fairlens-backend ^
    --region us-central1 ^
    --platform managed ^
    --allow-unauthenticated ^
    --port 8000 ^
    --memory 1Gi ^
    --cpu 1 ^
    --timeout 300s ^
    --concurrency 1000 ^
    --max-instances 10

for /f "delims=" %% tokens=1,2*" %%i in ('gcloud run services describe fairlens-backend --region us-central1 --format "value(status.url)"') do (
    set BACKEND_URL=%%i
)
cd ..
call :print_status "Deploying frontend to Firebase..."
cd frontend
set "REACT_APP_API_URL=%BACKEND_URL%"
npm run build
firebase deploy --project fairlens-bias-detection
cd ..
call :print_status "Deployment completed!"
call :print_status "Frontend: https://fairlens-bias-detection.web.app"
call :print_status "Backend: %BACKEND_URL%"
goto :eof

:deploy_render
call :print_status "Deploying to Render..."
cd backend
render deploy
for /f "delims=" %% tokens=1,2*" %%i in ('render ps --service fairlens-backend --format "json" ^| findstr /i "serviceUrl"') do (
    set BACKEND_URL=%%i
)
cd ..
call :print_status "Deploying frontend to Vercel..."
cd frontend
set "REACT_APP_API_URL=%BACKEND_URL%"
npm install
npm run build
vercel --prod
cd ..
call :print_status "Deployment completed!"
call :print_status "Frontend: https://fairlens-frontend.vercel.app"
call :print_status "Backend: %BACKEND_URL%"
goto :eof

:deploy_vercel
call :print_status "Deploying frontend to Vercel..."
cd frontend
set "REACT_APP_API_URL=https://fairlens-backend.onrender.com"
npm install
npm run build
vercel --prod
cd ..
call :print_status "Deployment completed!"
call :print_status "Frontend: https://fairlens-frontend.vercel.app"
goto :eof

:deploy_all
call :deploy_gcloud
call :deploy_vercel
call :print_status "Multi-platform deployment completed!"
call :print_status "Frontend: https://fairlens-frontend.vercel.app"
call :print_status "Backend: %BACKEND_URL%"
goto :eof

:help
echo FairLens Windows Deployment Script
echo.
echo Usage: deploy-windows.bat [platform]
echo.
echo Platforms:
echo   gcloud    - Google Cloud Run (Backend)
echo   render    - Render (Backend)  
echo   vercel    - Vercel (Frontend)
echo   all       - Deploy to all platforms
echo.
echo Examples:
echo   deploy-windows.bat gcloud     # Deploy backend to Google Cloud Run
echo   deploy-windows.bat render     # Deploy backend to Render
echo   deploy-windows.bat vercel     # Deploy frontend to Vercel
echo   deploy-windows.bat all        # Deploy to all platforms
echo.
echo.
goto :eof

:eof
endlocal
