import os
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse

import httpx

from app.exceptions import *


# ---------- Load environment variables correctly ----------
# assumes project structure:
#   project_root/.env
#   project_root/app/...
# If your .env is next to this file, change `.parent.parent` to `.parent`.
BASE_DIR = Path(__file__).resolve().parent.parent   # <-- CHECK THIS
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SCOPE = os.getenv("SCOPE")
REDIRECT_URI = os.getenv("REDIRECT_URI")
STATE = os.getenv("STATE")

print("DEBUG .env path:", ENV_PATH)
print("DEBUG CLIENT_ID:", CLIENT_ID)
print("DEBUG SCOPE:", SCOPE)
print("DEBUG STATE:", STATE)

# router for authorization urls
auth_router = APIRouter()


@auth_router.get("/oauth2callback")
async def oauth2callback(request: Request, state: str = None, code: str = None):
    """
    Step 1: no `code`  -> redirect user to Google OAuth consent screen
    Step 2: with `code` -> exchange authorization code for tokens
    """

    # ---------- STEP 1: redirect to Google ----------
    if code is None:
        # basic sanity check so we don't send malformed requests to Google
        if not CLIENT_ID or not SCOPE or not STATE or not REDIRECT_URI:
            return HTMLResponse(
                "OAuth env vars missing (CLIENT_ID / SCOPE / STATE / REDIRECT_URI). "
                "Check your .env and restart the server."
            )

        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,   # must match Google console
            "scope": SCOPE,
            "access_type": "offline",
            "state": STATE,
        }
        auth_uri = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
        print("DEBUG auth_uri:", auth_uri)

        return RedirectResponse(auth_uri)

    # ---------- STEP 2: callback from Google with ?code=... ----------
    print(f"DEBUG: Received callback: code={code[:10]}..., state={state}")

    # ensure that authorization request was called from our application
    if STATE != state:
        return HTMLResponse(
            f"Invalid state parameter. Please visit the "
            f"<a href={request.url_for('landing')}>web-app</a> to complete the authorization."
        )

    if not CLIENT_ID or not CLIENT_SECRET:
        return HTMLResponse(
            "CLIENT_ID or CLIENT_SECRET missing in env. Check your .env and restart the server."
        )

    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,  # must be the same as in STEP 1
        "grant_type": "authorization_code",
    }

    print("DEBUG: Exchanging code for token...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post("https://oauth2.googleapis.com/token", data=data)
    print("DEBUG token status:", response.status_code)
    print("DEBUG token body:", response.text)

    if response.status_code != 200:
        # This is usually where the 400 from Google will show real details:
        # e.g. redirect_uri_mismatch, invalid_grant, etc.
        return HTMLResponse(f"Token endpoint error ({response.status_code}): {response.text}")

    request.session["credentials"] = response.json()
    return RedirectResponse(request.url_for("home"))


@auth_router.get("/refresh-access-token")
async def refresh_access_token(request: Request):
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": request.session["credentials"]["refresh_token"],
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post("https://oauth2.googleapis.com/token", data=data)

    if response.status_code == 400:  # app's access revoked
        return HTMLResponse(
            f"Web-app's access to your youtube account has been revoked. "
            f"Please <a href={request.url_for('oauth2callback')}>authorize</a> to continue using the service."
        )

    credentials = response.json()
    request.session["credentials"]["access_token"] = credentials["access_token"]
    request.session["credentials"]["expires_in"] = credentials["expires_in"]

    redirect_url = request.session["redirect_url"]
    return RedirectResponse(redirect_url)


@auth_router.get("/revoke")
async def revoke(request: Request):
    if "credentials" not in request.session:
        return HTMLResponse(
            f"You need to <a href={request.url_for('oauth2callback')}>authorize</a> first before revoking the credentials."
        )

    credentials = request.session["credentials"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": credentials["access_token"]},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    if response.status_code == 403:
        return HTMLResponse("Cannot connect to youtube right now. Please comeback in a while.")

    elif response.status_code == 401:
        request.session["redirect_url"] = str(request.url)
        return RedirectResponse(request.url_for("refresh_access_token"))

    return RedirectResponse(request.url_for("logout"))


@auth_router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(request.url_for("landing"))
