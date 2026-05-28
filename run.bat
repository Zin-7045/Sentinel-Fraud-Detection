@echo off
cd /d "%~dp0"

echo ============================================
echo   Sentinel Fraud Detection Platform
echo ============================================

echo.
echo [1/4] Starting infrastructure services (Docker Compose)...
docker-compose up -d zookeeper kafka postgres redis mongodb spark-master spark-worker kafka-init
if %errorlevel% neq 0 (
    echo ERROR: Docker Compose failed. Is Docker running?
    pause
    exit /b 1
)

echo.
echo [2/4] Installing / verifying Python dependencies...
cd /d "%~dp0backend"
pip install -q fastapi uvicorn pydantic kafka-python redis psycopg2-binary pymongo scikit-learn numpy pandas joblib prometheus-client xgboost 2>nul
echo    Python dependencies ready.

echo.
echo [3/4] Starting backend API and Kafka producer...
start "Backend API" cmd /c "cd /d "%~dp0" && python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000"
echo    Waiting for API to be ready...
:wait_api
timeout /t 3 /nobreak >nul
curl -s -o nul http://localhost:8000/health 2>nul
if %errorlevel% neq 0 (
    goto wait_api
)
echo    API is ready at http://localhost:8000

echo    Seeding database with sample transactions...
cd /d "%~dp0"
python backend/pipeline/run_pipeline.py
echo    Database seeded with transactions + predictions.

start "Kafka Producer" cmd /c "cd /d "%~dp0" && python -c "from backend.streaming.kafka_producer import FraudKafkaProducer; kp = FraudKafkaProducer(); kp.stream_continuous(interval_ms=800)"
echo    Transaction stream producer started.

echo.
echo [4/4] Installing frontend dependencies...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    call npm install
    if %errorlevel% neq 0 (
        echo ERROR: npm install failed.
        pause
        exit /b 1
    )
) else (
    echo    node_modules found, skipping install.
)

start "Frontend" cmd /c "npx vite --host"
echo    Frontend starting at http://localhost:3001

echo.
echo ============================================
echo   All services starting up:
echo     Frontend : http://localhost:3001
echo     API Docs : http://localhost:8000/docs
echo     Spark UI : http://localhost:8080
echo ============================================
echo.
echo Close this window to stop, or press Ctrl+C
echo.

cd /d "%~dp0"
docker-compose logs -f
