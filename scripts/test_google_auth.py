from pathlib import Path
import gspread

ROOT = Path(__file__).resolve().parents[1]

CLIENT_SECRET = ROOT / "secrets" / "oauth-client.json"
TOKEN_FILE = ROOT / "secrets" / "authorized-user.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

if not CLIENT_SECRET.exists():
    raise FileNotFoundError(
        f"OAuth credentials not found: {CLIENT_SECRET}"
    )

client = gspread.oauth(
    credentials_filename=str(CLIENT_SECRET),
    authorized_user_filename=str(TOKEN_FILE),
    scopes=SCOPES,
)

print("Google authentication successful!")