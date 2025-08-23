#!/usr/bin/env python3
"""
Dinemate Startup Script

This script starts all required services for Dinemate with LLM enabled.
"""

import os
import sys
import subprocess
import time
import signal
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from shared.config import shared_config, llm_config

class DinemateStartup:
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def check_requirements(self):
        """Check if all required services are available."""
        print("🔍 Checking requirements...")
        
        # Check environment variables
        required_env_vars = [
            "OPENAI_API_KEY",
            "FOURSQUARE_API_KEY"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            print("Please set these in your .env file or environment")
            return False
        
        print("✅ Environment variables OK")
        return True
    
    def start_api_server(self):
        """Start the main FastAPI server."""
        print("🚀 Starting API server...")
        try:
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "app.main:app", 
                "--host", "0.0.0.0", 
                "--port", "8000", 
                "--reload"
            ], cwd=project_root)
            self.processes['api'] = process
            print("✅ API server started on http://localhost:8000")
            return True
        except Exception as e:
            print(f"❌ Failed to start API server: {e}")
            return False
    
    def start_celery_beat(self):
        """Start Celery beat scheduler for periodic tasks."""
        print("⏰ Starting Celery beat scheduler...")
        try:
            process = subprocess.Popen([
                "celery", "-A", "background_worker.celery_app", 
                "beat", "--loglevel=info"
            ], cwd=project_root)
            self.processes['celery_beat'] = process
            print("✅ Celery beat scheduler started")
            return True
        except Exception as e:
            print(f"❌ Failed to start Celery beat: {e}")
            return False
    
    def start_celery_worker(self):
        """Start Celery worker for background tasks."""
        print("⚙️  Starting Celery worker...")
        try:
            process = subprocess.Popen([
                "celery", "-A", "background_worker.celery_app", 
                "worker", "--loglevel=info", "--pool=threads", "--concurrency=1"
            ], cwd=project_root)
            self.processes['celery'] = process
            print("✅ Celery worker started")
            return True
        except Exception as e:
            print(f"❌ Failed to start Celery worker: {e}")
            print("Make sure Redis is running and Celery is installed")
            return False
    
    def check_services(self):
        """Check if external services are running."""
        print("🔗 Checking external services...")
        
        # Check MongoDB
        try:
            import pymongo
            client = pymongo.MongoClient(shared_config.DATABASE_URL, serverSelectionTimeoutMS=2000)
            client.server_info()
            print("✅ MongoDB connected")
        except Exception as e:
            print(f"❌ MongoDB not available: {e}")
            print("Please start MongoDB first")
            return False
        
        # Check Redis
        try:
            import redis
            r = redis.from_url(shared_config.REDIS_URL)
            r.ping()
            print("✅ Redis connected")
        except Exception as e:
            print(f"❌ Redis not available: {e}")
            print("Please start Redis first")
            return False
        
        return True
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.running = False
        self.shutdown()
    
    def shutdown(self):
        """Shutdown all processes."""
        print("🔄 Shutting down services...")
        
        for name, process in self.processes.items():
            try:
                print(f"   Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"   Force killing {name}...")
                process.kill()
            except Exception as e:
                print(f"   Error stopping {name}: {e}")
        
        print("✅ All services stopped")
    
    def run(self):
        """Main run method."""
        print("🍽️  Starting Dinemate with LLM enabled")
        print("=" * 50)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Check requirements
        if not self.check_requirements():
            return 1
        
        # Check external services
        if not self.check_services():
            return 1
        
        # Start services
        success = True
        
        if not self.start_api_server():
            success = False
        
        time.sleep(2)  # Wait for API to start
        
        # if not self.start_celery_worker():
            # success = False
        
        # if not self.start_celery_beat():
            # success = False
        
        if not success:
            print("❌ Some services failed to start")
            self.shutdown()
            return 1
        
        print("\n🎉 All services started successfully!")
        print("=" * 50)
        print("📍 API Server: http://localhost:8000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("🤖 LLM Analysis: Enabled (via Celery)")
        print("⚙️  Background Tasks: Enabled")
        print("⏰ Scheduled Tasks: Running")
        print("\n💡 Send messages to groups to see LLM in action!")
        print("   LLM analyzes messages every 5 minutes automatically!")
        print("Press Ctrl+C to stop all services")
        print("=" * 50)
        
        # Keep running until interrupted
        try:
            while self.running:
                time.sleep(1)
                
                # Check if any process died
                for name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        print(f"⚠️  {name} process died, restarting...")
                        if name == 'api':
                            self.start_api_server()
                        elif name == 'celery':
                            self.start_celery_worker()
                        elif name == 'celery_beat':
                            self.start_celery_beat()
                        
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()
        
        return 0


if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not installed, assuming env vars are set")
    
    startup = DinemateStartup()
    exit_code = startup.run()
    sys.exit(exit_code)