# Shared/automation_service.py
import asyncio
from MediaAutomation.automation_runner import run_bulk_automation

def run_automation_sync(file_list):
    return asyncio.run(run_bulk_automation(file_list))