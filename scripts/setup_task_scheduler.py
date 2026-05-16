import subprocess
import sys
from pathlib import Path

def create_task(task_name: str, time: str, script_path: str):
    """Create a Windows Task Scheduler task."""
    project_root = r"e:\AGENT"
    python_exe = r"e:\AGENT\venv\Scripts\python.exe"
    
    # We use cmd.exe /c to set the working directory before running python
    # This ensures relative paths inside the python scripts resolve correctly
    action = f'cmd.exe /c "cd /d {project_root} && {python_exe} {script_path}"'
    
    cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", action,
        "/sc", "DAILY",
        "/st", time,
        "/f"  # Force overwrite if exists
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Successfully created task: {task_name} at {time}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create task: {task_name}")
        print(f"Error: {e.stderr.strip() if e.stderr else e.stdout.strip()}")
        print("Note: You may need to run this script as Administrator.")

def setup_tasks():
    print("Setting up YT Shorts Agent background tasks...\n")
    
    tasks = [
        ("YT-Agent-Generate", "01:00", r"agent\run_generation.py"),
        ("YT-Agent-Upload-1", "09:00", r"uploader\upload_next.py"),
        ("YT-Agent-Upload-2", "15:00", r"uploader\upload_next.py"),
        ("YT-Agent-Upload-3", "20:00", r"uploader\upload_next.py"),
    ]
    
    for name, time, script in tasks:
        create_task(name, time, script)
        
    print("\n" + "="*60)
    print("IMPORTANT INSTRUCTIONS:")
    print("1. Open 'Task Scheduler' in Windows.")
    print("2. For each 'YT-Agent-*' task, right-click -> Properties.")
    print("3. Check 'Run whether user is logged on or not'.")
    print("4. Check 'Run with highest privileges'.")
    print("5. Enter your Windows password when prompted.")
    print("\nBefore relying on the scheduler:")
    print("  - Run 'python auth_flow.py' once to generate token.json")
    print("  - Run 'python agent/run_generation.py' manually once to test")
    print("="*60)

if __name__ == "__main__":
    setup_tasks()
