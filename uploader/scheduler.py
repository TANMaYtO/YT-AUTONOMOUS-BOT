"""Upload scheduler — Windows Task Scheduler integration.

NOT using APScheduler. Instead, this module provides helper functions
for creating/managing Windows Scheduled Tasks:

    1. create_generation_task() — schedules daily generation at 01:00
    2. create_upload_tasks() — schedules uploads at configured time slots
    3. list_agent_tasks() — shows all agent-related scheduled tasks
    4. remove_agent_tasks() — cleans up scheduled tasks

Each task runs a standalone Python script invocation:
    - python -m agent.run_generation  (for generation)
    - python -m uploader.upload_next  (for each upload slot)

No long-running process needed. OS-native reliability.
Survives reboots.

No logic implemented yet — placeholder for Phase 5.
"""

# import logging
# import subprocess
