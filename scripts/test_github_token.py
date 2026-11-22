import os

import httpx
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("GITHUB_TOKEN")

if not token:
    raise RuntimeError("GITHUB_TOKEN is missing from .env")

headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
    "User-Agent": "AI-Intelligence-Pipeline",
    "X-GitHub-Api-Version": "2022-11-28",
}

response = httpx.get(
    "https://api.github.com/user",
    headers=headers,
    timeout=20.0,
)

if response.status_code == 200:
    data = response.json()

    print("[SUCCESS] GitHub API authentication successful")
    print("Authenticated account:", data.get("login"))

elif response.status_code == 401:
    print("[ERROR] Invalid or expired GitHub token")

elif response.status_code == 403:
    print("[ERROR] GitHub denied access. Check token permissions.")

else:
    print("[ERROR] GitHub API request failed")
    print("HTTP status:", response.status_code)
    print("Response:", response.text[:300])