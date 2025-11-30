from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse

from app.library.youtube import fetchChannelData, fetchVideoData

from app.exceptions import *

from app.config import templates

import asyncio

home_view = APIRouter()


def compute_total_views(video_data: dict) -> int:
    if not video_data:
        return 0

    total = 0

    items = video_data.get("items", video_data)

    if isinstance(items, dict):
        iterable = items.values()
    else:
        iterable = items

    for video in iterable:
        if not isinstance(video, dict):
            continue
        view_count = video.get("views")
        if view_count is not None:
            try:
                total += int(view_count)
            except (TypeError, ValueError):
                continue

    return total


@home_view.get("")
async def home(request: Request):
    
    if "credentials" not in request.session:
        return RedirectResponse(request.url_for("oauth2callback"))
    
    try:
        if "channel_data" not in request.session:
            credentials = request.session["credentials"]
            channel_details = await fetchChannelData(credentials)

            video_data = await fetchVideoData(credentials)

            total_views = compute_total_views(video_data)

            request.session["channel_data"] = {
                "channel_details": channel_details,
                "video_data": video_data,
                "total_views": total_views,
            }

    except AccessTokenExpiredError:
        request.session["redirect_url"] = str(request.url)
        return RedirectResponse(request.url_for("refresh_access_token"))
        
    except EntityNotFoundError as entity_error: 
        if entity_error.entity == "channel":
            return HTMLResponse(
                f"<a href={request.url_for('revoke')}>Revoke access</a> for this account and authorize with a valid youtube channel."
            )
        
        elif entity_error.entity == "video":
            request.session.setdefault("channel_data", {})
            request.session["channel_data"]["video_data"] = {}
            request.session["channel_data"]["total_views"] = 0
    
    channel_details = request.session["channel_data"]["channel_details"]
    video_data = request.session["channel_data"]["video_data"]

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
    
    if "channel_data" in request.session:
        del request.session["channel_data"]
    
    return RedirectResponse(request.url_for("home"))
