import os

import httpx

from app.exceptions import *

# clint secret key for sending requests to yt api
KEY = os.getenv("CLIENT_SECRET")


async def fetchChannelData(credentials: dict) -> dict:
    """Fetches youtube channel data for authorized google account.

    Args:
        credentials (dict): Authorization credentials for accessing channel data.

    Raises:
        QuotaExceededError: If request quota is utilized.
        AccessTokenExpiredError: If access token in authorization header has expired.
        EntityNotFoundError: If youtube channel for authorized account doesn't exist.

    Returns:
        dict: Channel details of logged in user.
    """
    
    request_uri = "https://www.googleapis.com/youtube/v3/channels"
    
    headers = {
        "Authorization": f"Bearer {credentials['access_token']}",
        "Accept": "application/json"
    }
    
    params = {
        "mine": "true",
        "part": "snippet,contentDetails,statistics",
        "key": KEY
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(request_uri, params = params, headers = headers)
    
    # fails when quota exceeds or access token expires
    if response.status_code == 403:
        raise QuotaExceededError("Request quota exceeded for the day.")
    
    channel_resource = response.json()
    
    # if no channel / no videos / invalid id
    if "items" not in channel_resource or len(channel_resource["items"]) == 0:
        raise EntityNotFoundError("channel", "Authorized youtube account haven't uploaded videos.")
    
    channel_item = channel_resource["items"][0]
    
    channel_details = {
        "name": channel_item["snippet"]["title"],
        "logo_url": channel_item["snippet"]["thumbnails"]["medium"]["url"],
        "stats": {
            "viewCount": channel_item["statistics"].get("viewCount", 0),
            "subscriberCount": channel_item["statistics"].get("subscriberCount", 0),
            "videoCount": channel_item["statistics"].get("videoCount", 0)
        }
    }
    
    return channel_details


async def fetchVideoData(credentials: dict) -> dict:
    """Fetches video data for authorized google account.

    Args:
        credentials (dict): Authorization credentials for accessing channel data.

    Raises:
        QuotaExceededError: If request quota is utilized.
        AccessTokenExpiredError: If access token in authorization header has expired.
        EntityNotFoundError: If videos for logged in channel doesn't exist.

    Returns:
        dict: Video data for latest 50 videos of the user.
    """
    
    request_uri = "https://www.googleapis.com/youtube/v3/search"
    
    headers = {
        "Authorization": f"Bearer {credentials['access_token']}",
        "Accept": "application/json"
    }

    params = {
        "part": "snippet",
        "forMine": "true",
        "maxResults": 50,    # get latest 50 videos from channel
        "order": "date",
        "type": "video",
        "key": KEY
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(request_uri, params = params, headers = headers)
    
    # fails when quota exceeds or access token expires
    if response.status_code == 403:
        raise QuotaExceededError("Request quota exceeded for the day.")
    
    elif response.status_code == 401:
        raise AccessTokenExpiredError("Current access token expired, get a fresh one.")
    
    video_resource = response.json()
    
    # if no videos uploaded
    if "items" not in video_resource or len(video_resource["items"]) == 0:
        raise EntityNotFoundError("video", "Authorized youtube account haven't uploaded videos.")
    
    # extract video ids from video resource
    video_ids = ",".join(resource["id"]["videoId"] for resource in video_resource["items"])
    
    # get video data from obtained video ids
    request_uri = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "snippet,contentDetails,statistics",
        "id": video_ids,
        "key": KEY
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(request_uri, params = params, headers = headers)
    
    # fails when quota exceeds or access token expires
    if response.status_code == 403:
        raise QuotaExceededError("Request quota exceeded for the day.")
    
    elif response.status_code == 401:
        raise AccessTokenExpiredError("Current access token expired, get a fresh one.")
    
    video_details = response.json()
    
    # extract required video data
    video_data = {}
    
    for data in video_details["items"]:
        video_data[data["id"]] = {
            "id": data["id"],
            "title": data["snippet"]["title"],
            "views": data["statistics"]["viewCount"],
            "likes": data["statistics"]["likeCount"],
            "comments": data["statistics"]["commentCount"],
            "description": data["snippet"]["description"][:100],
            "thumbnail_url": data["snippet"]["thumbnails"]["medium"]["url"]
        }
    
    return video_data


async def fetchVideoComments(credentials: dict, video_id: str):
    """Generator function fetches comments for given youtube video id.

    Args:
        credentials (dict): Authorization credentials for accessing channel data.
        video_id (str): Video id corresponding to which fetch comments.

    Raises:
        QuotaExceededError: If request quota is utilized.
        AccessTokenExpiredError: If access token in authorization header has expired.
        EntityNotFoundError: If comments for given video id doesn't exist.

    Returns:
        AsyncGenerator: An async generator object which can be iterated over to get dict containing comments data for specified video.
    """
    
    pageToken = ""
    
    request_uri = "https://www.googleapis.com/youtube/v3/commentThreads"
    
    headers = {
        "Authorization": f"Bearer {credentials['access_token']}",
        "Accept": "application/json"
    }
    
    # yt api allows fetching only 100 comments at a time hence repeat to fetch all comments
    while True:
        params = {
            "part": "snippet",
            "maxResults": 100,
            "pageToken": pageToken,
            "videoId": video_id,
            "textFormat": "plainText",
            "moderationStatus": "published",  # ✅ Only visible comments
            "key": KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(request_uri, params = params, headers = headers)
        
        # fails when quota exceeds or access token expires
        if response.status_code == 403:
            raise QuotaExceededError("Request quota exceeded for the day.")
        
        elif response.status_code == 401:
            raise AccessTokenExpiredError("Current access token expired, get a fresh one.")
        
        comment_threads = response.json()
        
        # if there are no comments posted
        if "items" not in comment_threads or len(comment_threads["items"]) == 0:
            raise EntityNotFoundError("comment_thread", "Selected video doesn't have any comments")
        
        comment_dict = {"id": [], "comment_text": []}
        for comment in comment_threads["items"]:
            comment_dict["id"].append(comment['snippet']['topLevelComment']['id'])
            comment_dict["comment_text"].append(comment['snippet']['topLevelComment']['snippet']['textDisplay'])
        
        # send data to analysis view and go to next iteration if possible
        yield comment_dict
        
        if "nextPageToken" in comment_threads:
            pageToken = comment_threads["nextPageToken"]
        else:
            break
        
        
# app/library/youtube_sync.py
import os
import requests
from typing import List

# import your exception types (fallback to Exception if not defined)
try:
    from app.exceptions import AccessTokenExpiredError, QuotaExceededError
except Exception:
    AccessTokenExpiredError = Exception
    QuotaExceededError = Exception

_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
_CLIENT_ID = os.getenv("CLIENT_ID")
_CLIENT_SECRET = os.getenv("CLIENT_SECRET")


async def rejectComments(credentials: dict, toxic_ids: List[str]) -> None:
    """
    Set moderation status of toxic comment ids to 'rejected'.
    Wrapper around sync implementation for backward compatibility.
    """
    # Run sync function in thread pool to avoid blocking event loop
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: reject_comments_sync(credentials, toxic_ids))

def reject_comments_sync(credentials: dict, toxic_ids: List[str]) -> None:
    """
    Set moderation status of toxic comment ids to 'rejected' (synchronous).
    Updates credentials['access_token'] in-place if refresh occurs.

    Raises:
      - QuotaExceededError for 403
      - AccessTokenExpiredError for 401 and refresh failures
      - Exception for other unexpected failures (includes API response text)
    """
    if not toxic_ids:
        return

    request_uri = "https://www.googleapis.com/youtube/v3/comments/setModerationStatus"
    params = {
        "id": ",".join(str(i) for i in toxic_ids),
        "moderationStatus": "rejected",
    }

    def _do_request(access_token: str):
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        resp = requests.post(request_uri, params=params, headers=headers, timeout=30)
        return resp

    access_token = credentials.get("access_token")
    if not access_token:
        raise AccessTokenExpiredError("No access_token in credentials.")

    print(f"DEBUG: Rejecting IDs: {toxic_ids}")
    # 1) Try with current access token
    resp = _do_request(access_token)
    print(f"DEBUG: Reject Response ({resp.status_code}): {resp.text}")

    if resp.status_code in (200, 204):
        return

    if resp.status_code == 403:
        # 403 could be quota or insufficient permission
        raise QuotaExceededError(f"403 Forbidden: {resp.text}")

    if resp.status_code == 401:
        # Try refresh if refresh_token is available
        refresh_token = credentials.get("refresh_token")
        if not refresh_token:
            raise AccessTokenExpiredError(f"401 Unauthorized and no refresh_token available. Response: {resp.text}")

        if not _CLIENT_ID or not _CLIENT_SECRET:
            raise AccessTokenExpiredError("CLIENT_ID/CLIENT_SECRET missing; cannot refresh token.")

        token_payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
        }

        token_resp = requests.post(_OAUTH_TOKEN_URL, data=token_payload, timeout=30)
        if token_resp.status_code != 200:
            raise AccessTokenExpiredError(f"Token refresh failed: {token_resp.status_code} - {token_resp.text}")

        token_json = token_resp.json()
        new_access_token = token_json.get("access_token")
        if not new_access_token:
            raise AccessTokenExpiredError(f"Refresh response missing access_token: {token_resp.text}")

        # Update credentials dict in-place so caller (session/db) can persist it if needed
        credentials["access_token"] = new_access_token
        if "expires_in" in token_json:
            credentials["expires_in"] = token_json["expires_in"]
        if "scope" in token_json:
            credentials["scope"] = token_json["scope"]

        # 2) Retry moderation with refreshed token
        retry_resp = _do_request(new_access_token)
        if retry_resp.status_code in (200, 204):
            return

        if retry_resp.status_code == 403:
            raise QuotaExceededError(f"403 after refresh: {retry_resp.text}")
        if retry_resp.status_code == 401:
            raise AccessTokenExpiredError(f"401 after refresh: {retry_resp.text}")

        raise Exception(f"Failed to set moderation after refresh. HTTP {retry_resp.status_code}: {retry_resp.text}")

    # other unexpected errors
    raise Exception(f"Failed to set moderation. HTTP {resp.status_code}: {resp.text}")
