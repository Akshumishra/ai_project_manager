import sys
import os
import asyncio
import logging

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.backend.services.standup_scheduler import standup_scheduler

# Configure logging to see the output from the jobs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    print("--- Starting Instant Scheduler Verification ---")
    
    # Verify Morning Job
    print("\n[1/2] Manually triggering MORNING job (Standup Initiation)...")
    await standup_scheduler.morning_job()
    
    # Verify Evening Job
    print("\n[2/2] Manually triggering EVENING job (Standup Finalization)...")
    await standup_scheduler.evening_job()
    
    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
