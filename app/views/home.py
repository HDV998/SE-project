from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse

from library.youtube import fetchChannelData, fetchVideoData

from exceptions import *

from config import templates

import asyncio

home_view = APIRouter()


def compute_total_views(video_data: dict) -> int:
    """Return sum of view counts from video_data."""
    if not video_data:
        return 0

    total = 0

    # video_data might be {"items": [...]}, a list, or a dict of id -> video
    items = video_data.get("items", video_data)

    if isinstance(items, dict):
        iterable = items.values()
    else:
        iterable = items

    for video in iterable:
        if not isinstance(video, dict):
            continue
        # video_data structure from youtube.py has 'views' at top level
        view_count = video.get("views")
        if view_count is not None:
            try:
                total += int(view_count)
            except (TypeError, ValueError):
                # ignore bad values
                continue

    return total


@home_view.get("")
async def home(request: Request):
    """Home page of the web-app.

    Args:
        request (Request): A Request object containing request data sent from client side.

    Returns:
        RedirectReponse: If user is not authorized, redirect to authorize. 
        HTMLResponse: If an exception occurs, generic page stating the exception is displayed.
        TemplateResponse: Home page with context-dict containing necessary data.
    """
    
    # if not authorized, authorize first
    if "credentials" not in request.session:
        return RedirectResponse(request.url_for("oauth2callback"))
    
    try:
        if "channel_data" not in request.session:
            credentials = request.session["credentials"]
            channel_details = await fetchChannelData(credentials)

            video_data = await fetchVideoData(credentials)

            # compute total views from all videos
            total_views = compute_total_views(video_data)

            request.session["channel_data"] = {
                "channel_details": channel_details,
                "video_data": video_data,
                "total_views": total_views,
            }

    except AccessTokenExpiredError:
        request.session["redirect_url"] = str(request.url)
        return RedirectResponse(request.url_for("refresh_access_token"))
        
    except EntityNotFoundError as entity_error:  # no channel or videos not found
        if entity_error.entity == "channel":
            return HTMLResponse(
                f"<a href={request.url_for('revoke')}>Revoke access</a> for this account and authorize with a valid youtube channel."
            )
        
        elif entity_error.entity == "video":
            # ensure channel_data dict exists
            request.session.setdefault("channel_data", {})
            request.session["channel_data"]["video_data"] = {}
            request.session["channel_data"]["total_views"] = 0
    
    channel_details = request.session["channel_data"]["channel_details"]
    video_data = request.session["channel_data"]["video_data"]

    # get total views; if missing (old session), compute once
    total_views = request.session["channel_data"].get("total_views")
    if total_views is None:
        total_views = compute_total_views(video_data)
        request.session["channel_data"]["total_views"] = total_views
        
    context_dict = {
        "request": request,
        "channel_details": channel_details,
        "video_data": video_data,
        "total_views": total_views,
    }
    
    return templates.TemplateResponse("home.html", context=context_dict)


@home_view.get("/refresh-home")
async def refresh_home(request: Request):
    """Clears the channel data stored in session storage.

    Args:
        request (Request): A Request object containing request data sent from client side.

    Returns:
        RedirectResponse: Redirects to home page where updated channel data is fetched.
    """
    
    if "channel_data" in request.session:
        del request.session["channel_data"]
    
    return RedirectResponse(request.url_for("home"))
