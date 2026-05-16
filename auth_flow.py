from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path
import json

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CREDENTIALS_PATH = Path("credentials/google_oauth.json")
TOKEN_PATH = Path("credentials/token.json")

def run_auth_flow():
    if not CREDENTIALS_PATH.exists():
        print(f"❌ Error: {CREDENTIALS_PATH} not found.")
        print("Please download your OAuth 2.0 Client ID JSON from Google Cloud Console and save it to this path.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_PATH), SCOPES
    )
    # Opens browser for one-time login
    creds = flow.run_local_server(port=0)
    
    # Save token
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    print(f"✅ token.json saved to {TOKEN_PATH}")
    print("Do not commit this file. It is in .gitignore.")

if __name__ == "__main__":
    run_auth_flow()
