import os
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import templates
from app.auth import auth_router
from app.views import home_view, analysis_view

from app.machine_learning import load_tokeninzer, load_model


load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
app.add_middleware(SessionMiddleware, secret_key = os.getenv("SESSION_SECRET"))


@app.on_event("startup")
def startup_event():
    
    load_tokeninzer()
    load_model()


@app.get("/", tags=["Landing Page"])
def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


# adding various routes to the app
app.include_router(auth_router, tags=["Google OAuth 2.0"], prefix="/auth")
app.include_router(home_view, tags=["Home"], prefix="/home")
app.include_router(analysis_view, tags=["Video Analysis"], prefix="/video-analysis")