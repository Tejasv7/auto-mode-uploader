import os
import json
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from config.settings import CONFIG_DIR

# Scopes required for YouTube Video Upload
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

class YouTubeUploader:
    """
    Automated YouTube Video Uploader using YouTube Data API v3.
    Requires client_secrets.json inside config/ directory.
    """
    def __init__(self, secrets_file: Path = CONFIG_DIR / "client_secrets.json", token_file: Path = CONFIG_DIR / "token.json"):
        self.secrets_file = secrets_file
        self.token_file = token_file
        self.service = None

    def is_configured(self) -> bool:
        """Check if client_secrets or existing token exists."""
        return self.secrets_file.exists() or self.token_file.exists()

    def authenticate(self):
        """Authenticate with YouTube via OAuth2."""
        creds = None
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            except Exception as e:
                print(f"  [!] Failed to load saved token: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.secrets_file.exists():
                    raise FileNotFoundError(
                        f"Missing YouTube OAuth file: {self.secrets_file}\n"
                        "Please download client_secret.json from Google Cloud Console "
                        "and save it as 'config/client_secrets.json'."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(self.secrets_file), SCOPES)
                creds = flow.run_local_server(port=0)

            with open(self.token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

        self.service = build("youtube", "v3", credentials=creds)
        print("  [+] YouTube authentication successful!")

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list = None,
        category_id: str = "24",  # 24 = Entertainment
        privacy_status: str = "private"  # 'private', 'unlisted', or 'public'
    ) -> str:
        """Upload video to YouTube and return video ID."""
        if not self.is_configured():
            print("\n" + "="*60)
            print("[INFO] YouTube Auto-Upload is skipped because 'config/client_secrets.json' is not configured.")
            print(f"Your video has been saved locally at: {video_path}")
            print("To enable auto-upload later, place client_secrets.json in the config folder.")
            print("="*60 + "\n")
            return None

        if not self.service:
            self.authenticate()

        body = {
            "snippet": {
                "title": title[:100],  # YouTube max title length
                "description": description,
                "tags": tags or ["shorts", "story"],
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

        print(f"\n[*] Uploading video '{title}' to YouTube ({privacy_status})...")
        request = self.service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  [~] Upload progress: {int(status.progress() * 100)}%")

        video_id = response.get("id")
        video_url = f"https://youtu.be/{video_id}"
        print(f"\n[SUCCESS] Video Uploaded Successfully! Link: {video_url}")
        return video_url


if __name__ == "__main__":
    uploader = YouTubeUploader()
    if uploader.is_configured():
        print("YouTube uploader is ready to upload.")
    else:
        print("YouTube uploader: client_secrets.json not found (will save videos locally).")
