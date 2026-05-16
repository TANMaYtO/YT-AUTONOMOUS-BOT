"""Node 7 — Queue Manager.

Saves the final video path + all metadata + assigned upload time
slot to queue.json.

Safety:
    - All queue.json access uses filelock
    - Writes use atomic write-then-rename (os.replace)
    - Validates video_validated is True before accepting

Status lifecycle: "pending" → "uploaded" | "failed"

Writes to state:
    queue_entry_id, scheduled_upload_time
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from filelock import FileLock

from agent.state import validate_state_for_node

logger = logging.getLogger(__name__)

async def manage_queue(
    state: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Node 7: Add video to upload queue."""
    logger.info(f"[queue_manager] Starting")

    if state.get("error"):
        return state

    validation_error = validate_state_for_node(state, "queue_manager")
    if validation_error:
        logger.error(f"[queue_manager] {validation_error}")
        return {**state, "error": validation_error, "failed_node": "queue_manager"}

    try:
        # Read the assigned slot from config injected by orchestrator
        upload_dt = config.get("_current_upload_dt")
        if not upload_dt:
            logger.warning("[queue_manager] No upload time provided in config, using dummy fallback.")
            upload_dt = "2099-01-01T00:00:00+00:00"

        # Generate unique ID
        entry_id = str(uuid.uuid4())
        
        project_root = Path(__file__).resolve().parent.parent.parent
        queue_file = project_root / config.get("paths", {}).get("queue", "queue.json")
        lock_file = str(queue_file) + ".lock"

        # Ensure directory exists
        queue_file.parent.mkdir(parents=True, exist_ok=True)

        new_entry = {
            "id": entry_id,
            "status": "pending",
            "scheduled_upload_time": upload_dt,
            "created_at": state["created_at"],
            "video_path": state["final_video"],
            "title": state["title"],
            "description": state["description"],
            "tags": state.get("tags", []),
        }

        # Safe read/write
        with FileLock(lock_file):
            if queue_file.exists():
                with open(queue_file, "r", encoding="utf-8") as f:
                    try:
                        queue_data = json.load(f)
                    except json.JSONDecodeError:
                        queue_data = []
            else:
                queue_data = []
            
            queue_data.append(new_entry)
            
            temp_file = queue_file.with_suffix('.tmp')
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(queue_data, f, indent=2)
            os.replace(temp_file, queue_file)

        logger.info(f"[queue_manager] Added to queue: {entry_id} for {upload_dt}")
        
        return {
            **state,
            "queue_entry_id": entry_id,
            "scheduled_upload_time": upload_dt
        }
        
    except Exception as e:
        logger.error(f"[queue_manager] Failed: {e}")
        return {
            **state,
            "error": f"Queue manager failed: {e}",
            "failed_node": "queue_manager"
        }
