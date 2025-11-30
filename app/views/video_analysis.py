import os

from fastapi import APIRouter, Request, Response, Body
from fastapi.responses import RedirectResponse, HTMLResponse

from app.library.youtube import fetchVideoComments, rejectComments
from app.library.video_analysis import VideoAnalysis

from app.exceptions import *

from app.config import templates


analysis_view = APIRouter()

@analysis_view.get("/{video_id}")
async def video_analysis(request: Request, video_id: str):
    
    if "channel_data" not in request.session:
        return RedirectResponse(request.url_for("home"))
    analysis_obj = VideoAnalysis()
    
    try:
        comment_itr = fetchVideoComments(request.session["credentials"], video_id)        
        async for comment_dict in comment_itr:
            analysis_obj.appendComments(comment_dict)
        
    except QuotaExceededError: 
        return HTMLResponse("Cannot connect to youtube right now. Please comeback in a while.")
    
    except AccessTokenExpiredError: 
        request.session["redirect_url"] = str(request.url)
        return RedirectResponse(request.url_for("refresh_access_token"))
    
    except EntityNotFoundError: 
        has_comments = False
    
    else:
        has_comments = True

        
        analysis_obj.classifyComments()
        analysis_obj.createWordCloud(video_id)
        analysis_obj.createClassificationGraph(video_id)
        
        toxic_ids = analysis_obj.getToxicIds()
        request.session["channel_data"]["video_data"][video_id]["toxic_ids"] = toxic_ids

        comments = analysis_obj.comments_df.to_dict("records")
    
    context_dict = {
        "request": request,
        "channel_details": request.session["channel_data"]["channel_details"],
        "video": request.session["channel_data"]["video_data"][video_id],
        "video_id": video_id,
        "has_comments": has_comments,
        "comments": comments
    }
    
    return templates.TemplateResponse("video_analysis.html", context = context_dict)


@analysis_view.delete("/delete-graphs/{video_id}")
async def delete_graphs(video_id: str):
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    word_cloud_path = os.path.join(base_dir, "static", "images", f"word_cloud_{video_id}.png")
    classification_graph_path = os.path.join(base_dir, "static", "images", f"classification_graph_{video_id}.png")

    if os.path.exists(word_cloud_path):
        os.remove(word_cloud_path)
        
    if os.path.exists(classification_graph_path):
        os.remove(classification_graph_path)
        
    return Response(status_code = 200)
        

@analysis_view.get("/reject-comments/{video_id}")
async def reject_comments(request: Request, video_id: str):
    
    if "toxic_ids" not in request.session["channel_data"]["video_data"][video_id]:
        return RedirectResponse(request.url_for("video_analysis", video_id = video_id))
    
    toxic_ids = request.session["channel_data"]["video_data"][video_id]["toxic_ids"]
    
    try:
        await rejectComments(request.session["credentials"], toxic_ids)
    
    except QuotaExceededError: 
        return HTMLResponse("Cannot connect to youtube right now. Please comeback in a while..")
    
    except AccessTokenExpiredError: 
        request.session["redirect_url"] = str(request.url)
        return RedirectResponse(request.url_for("refresh_access_token"))
    del request.session["channel_data"]["video_data"][video_id]["toxic_ids"]
    
    return RedirectResponse(request.url_for("video_analysis", video_id = video_id))

@analysis_view.post("/delete-selected-comments/{video_id}")
async def delete_selected_comments(
    request: Request,
    video_id: str,
    comment_ids: list[str] = Body(...)
):
    if "credentials" not in request.session:
        raise PermissionDeniedError("Login required.")
    
    if not comment_ids:
        return {"status": "error", "message": "No comments selected."}
    
    await rejectComments(request.session["credentials"], comment_ids)
    
    return {
        "status": "success", 
        "message": f"{len(comment_ids)} comments deleted successfully."
    }