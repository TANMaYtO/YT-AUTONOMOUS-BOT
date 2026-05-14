"""YouTube Data API v3 uploader.

Handles uploading videos to YouTube as Shorts:
    - Loads OAuth2 credentials from credentials/token.json
    - Reads next "pending" entry from queue.json (filelock-guarded)
    - Uploads video with title, description, tags
    - Updates queue entry to "uploaded" with YouTube video ID
    - Custom retry: transient (5xx) errors only, max 1 retry
    - YouTube auto-classifies vertical <60s videos as Shorts

Quota budget: 1,600 units per upload, 10,000 units/day.
With 1 retry cap: worst case 3,200 units per failed video.

No logic implemented yet — placeholder for Phase 5.
"""

# import logging
# from pathlib import Path
#
# from filelock import FileLock
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload
# from tenacity import retry, stop_after_attempt, retry_if_exception
