import streamlit as st
import os
import sys
import asyncio
import httpx
import urllib.parse
from dotenv import load_dotenv
import datetime

# ---------- PATH & ENV SETUP ----------

# Add project root to path (so we can import app.*)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables from app-streamlit/.env
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# ---------- IMPORTS FROM MAIN APP ----------
from app.machine_learning import load_tokeninzer, load_model
from app.library.youtube import (
    fetchChannelData,
    fetchVideoData,
    fetchVideoComments,
    rejectComments,
)
from app.library.video_analysis import VideoAnalysis
from app.exceptions import *

# ---------- CONSTANTS ----------
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPE = os.getenv("SCOPE")
STATE = os.getenv("STATE")

# ---------- STREAMLIT PAGE CONFIG ----------
st.set_page_config(
    page_title="DeTox | Clean Your Comments",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",  # sidebar will start hidden
)

# ---------- GLOBAL STYLES ----------
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Oswald:wght@500;700&display=swap');

    /* MAIN APP */
    .stApp {
        background-color: #050b1f;
        font-family: 'Inter', sans-serif;
        color: #e5e7eb;
    }

    header[data-testid="stHeader"] {
        background: #050b1f;
    }

    main.block-container {
        padding-top: 0rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }

    /* HIDE SIDEBAR COMPLETELY */
    [data-testid="stSidebar"] {
        display: none !important;
    }

    /* TOP NAV BUTTONS */
    .top-logo {
        font-family: 'Oswald', sans-serif;
        font-size: 1.4rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #f9fafb;
    }

    /* BUTTONS (all) */
    .stButton > button {
        background: #111827;
        color: #e5e7eb;
        border-radius: 999px;
        font-weight: 600;
        text-transform: uppercase;
        border: 1px solid #1f2937;
        padding: 0.5rem 1.4rem;
        transition: all 0.18s ease-in-out;
        font-family: 'Oswald', sans-serif;
        letter-spacing: 0.08em;
        font-size: 0.8rem;
    }
    .stButton > button:hover {
        background: #1f2937;
        transform: translateY(-1px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.35);
    }

    /* HERO SECTION – DARK */
    .hero {
        background: #0b1120;
        color: #f9fafb;
        border-radius: 0 0 32px 32px;
        position: relative;
        padding: 2.5rem 3rem 2.7rem 3rem;
        /* sit neatly under the top buttons */
        margin: 0 -3rem 2.0rem -3rem;
    }

    .hero-inner {
        max-width: 1120px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        gap: 2.4rem;
    }

    .hero-main {
        text-align: center;
        padding: 1.2rem 0 0.5rem;
    }

    .hero-title {
        font-family: 'Oswald', sans-serif;
        font-size: clamp(3rem, 6vw, 4.6rem);
        line-height: 1.02;
        text-transform: uppercase;
        letter-spacing: 0.12em;
    }

    .hero-subtitle {
        margin-top: 1.2rem;
        font-size: 1.02rem;
        max-width: 640px;
        margin-left: auto;
        margin-right: auto;
        opacity: 0.9;
    }

    .hero-stats-row {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        justify-content: center;
        margin-top: 1.4rem;
    }

    .hero-stat-pill {
        background: #020617;
        border-radius: 999px;
        padding: 0.55rem 1.4rem;
        font-size: 0.78rem;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        border: 1px solid #1f2937;
    }

    /* CARDS */
    .css-card {
        background: #020617;
        padding: 1.5rem 1.6rem;
        border-radius: 18px;
        box-shadow: 0 16px 40px rgba(0,0,0,0.65);
        margin-bottom: 1.4rem;
        color: #e5e7eb;
        border: 1px solid #1f2937;
    }

    .video-card {
        height: 100%;
        display: flex;
        flex-direction: column;
        gap: 0.7rem;
    }

    .video-card-title {
        font-family: 'Oswald', sans-serif;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.2rem;
        font-size: 0.95rem;
        color: #f9fafb;
    }

    .video-meta {
        font-size: 0.8rem;
        color: #9ca3af;
    }

    /* METRICS */
    [data-testid="stMetricValue"] {
        color: #60a5fa;
        font-weight: 700;
    }

    /* REVIEWS */
    .review-card {
        background: #020617;
        padding: 1.6rem 1.8rem;
        border-radius: 18px;
        box-shadow: 0 16px 40px rgba(0,0,0,0.65);
        margin-bottom: 1.2rem;
        color: #e5e7eb;
        border: 1px solid #1f2937;
    }

    .stars {
        color: #4ade80;
        font-weight: 700;
    }

    .verified {
        color: #9ca3af;
        font-size: 0.8rem;
        margin-left: 0.35rem;
    }

</style>
""",
    unsafe_allow_html=True,
)


# ---------- MODEL CACHING ----------
@st.cache_resource
def init_models():
    load_tokeninzer()
    load_model()


init_models()

# ---------- HELPER FUNCTIONS ----------


def get_login_url() -> str:
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "access_type": "offline",
        "state": STATE,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(
        params
    )


async def exchange_code(code: str):
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post("https://oauth2.googleapis.com/token", data=data)
    return response


def refresh_analysis_from_youtube(credentials, video_id: str):
    """
    Create a fresh VideoAnalysis object by fetching current comments from YouTube,
    classifying them, and generating visual artifacts. Returns the new analysis_obj.
    """
    analysis_obj = VideoAnalysis()
    try:
        # fetch and consume comments
        comment_itr = fetchVideoComments(credentials, video_id)

        async def consume_comments():
            async for comment_dict in comment_itr:
                analysis_obj.appendComments(comment_dict)

        asyncio.run(consume_comments())

        # If no comments, return the empty analysis object (caller will handle)
        if analysis_obj.comments_df.empty:
            return analysis_obj

        # Classify and recreate visuals
        analysis_obj.classifyComments()
        analysis_obj.createWordCloud(video_id)
        analysis_obj.createClassificationGraph(video_id)

        return analysis_obj

    except Exception:
        # Let caller handle exceptions
        raise


# ---------- MAIN APP ----------


def main():
    # ---- STATE INITIALIZATION ----
    if "page" not in st.session_state:
        st.session_state.page = "Home"
    if "credentials" not in st.session_state:
        st.session_state.credentials = None

    # ---- TOP NAVBAR (logo left, buttons right) ----
    nav_left, nav_right = st.columns([1, 3])
    with nav_left:
        st.markdown('<div class="top-logo">DETOX</div>', unsafe_allow_html=True)

    with nav_right:
        c_home, c_about, c_stories, c_refresh, c_logout = st.columns([1, 1, 1, 1, 1])

        if c_home.button("HOME"):
            st.session_state.page = "Home"
        if c_about.button("ABOUT"):
            st.session_state.page = "About"
        if c_stories.button("STORIES"):
            st.session_state.page = "Stories"

        # Refresh content: clear cached video data so it is fetched again
        if c_refresh.button("REFRESH"):
            st.session_state.pop("video_data", None)
            st.session_state.pop("channel_data_cache", None)
            st.session_state.pop("analysis_obj", None)
            st.session_state.pop("analysis_video_id", None)
            st.rerun()

        # Logout button only works if user is logged in
        if st.session_state.credentials and c_logout.button("LOGOUT"):
            st.session_state.credentials = None
            st.rerun()

    st.write("")  # small spacer under nav

    # ---- HANDLE OAUTH CALLBACK ----
    query_params = st.query_params
    if "code" in query_params and st.session_state.credentials is None:
        code = query_params["code"]
        with st.spinner("Authenticating..."):
            response = asyncio.run(exchange_code(code))
            if response.status_code == 200:
                st.session_state.credentials = response.json()
                st.query_params.clear()
                st.rerun()
            else:
                st.error(f"Authentication failed: {response.text}")

    # ---- PAGE ROUTING ----
    page = st.session_state.page
    if page == "Home":
        render_home()
    elif page == "About":
        render_about()
    elif page == "Stories":
        render_stories()


# ---------- HOME / HERO + DASHBOARD ----------


def render_home():
    creds = st.session_state.credentials

    # ---------- LOGGED OUT: HERO LANDING ----------
    if creds is None:
        login_url = get_login_url()
        st.markdown(
            f"""
        <div class="hero">
          <div class="hero-inner">
            <div class="hero-main">
              <div class="hero-title">
                CLEAN UP<br/>THE TOXICITY
              </div>
              <div class="hero-subtitle">
                Deep learning powered moderation for your YouTube channel.
                Automatically detect and remove hate speech, threats, and insults —
                before they reach your community.
              </div>
              <div class="hero-cta" style="margin-top: 2.0rem;">
                <a href="{login_url}" target="_self">
                  <button>GET STARTED</button>
                </a>
              </div>
            </div>
            <div class="hero-stats-row">
              <div class="hero-stat-pill">NO CODE SETUP</div>
              <div class="hero-stat-pill">REAL-TIME MODERATION</div>
              <div class="hero-stat-pill">BUILT FOR CREATORS</div>
            </div>
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
        <div class="css-card">
            <h3>How it works</h3>
            <p>Connect your YouTube channel with a single click. DeTox ingests comments,
            classifies them using a fine-tuned deep learning model, and lets you bulk delete
            toxic content in seconds.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    # ---------- LOGGED IN: DASHBOARD HERO + VIDEO GRID ----------

    # cache channel data so REFRESH can clear and force re-fetch
    if "channel_data_cache" not in st.session_state:
        try:
            st.session_state.channel_data_cache = asyncio.run(fetchChannelData(creds))
        except Exception as e:
            st.error(f"Error fetching channel data: {e}")
            return

    channel_data = st.session_state.channel_data_cache

    st.markdown(
        f"""
    <div class="hero" style="margin-bottom: 1.5rem;">
      <div class="hero-inner">
        <div class="hero-main" style="padding-top: 0.8rem;">
          <div style="
                font-family: 'Oswald', sans-serif;
                letter-spacing: 0.18em;
                text-transform: uppercase;
                font-size: 0.9rem;
                text-align: left;
            ">
            DETOX • DASHBOARD
          </div>
          <div class="hero-title" style="font-size: clamp(2.3rem, 4vw, 3.4rem); margin-top: 0.6rem;">
            Welcome back, {channel_data['name']}
          </div>
          <div class="hero-subtitle">
            Your channel’s health at a glance. Review toxicity, understand your audience,
            and keep your community safe.
          </div>
        </div>
        <div class="hero-stats-row">
          <div class="hero-stat-pill">SUBSCRIBERS: {channel_data['stats']['subscriberCount']}</div>
          <div class="hero-stat-pill">TOTAL VIEWS: {channel_data['stats']['viewCount']}</div>
          <div class="hero-stat-pill">VIDEOS: {channel_data['stats']['videoCount']}</div>
        </div>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ---------- VIDEO ANALYSIS GRID ----------
    st.markdown("### Video Analysis")

    # fetch videos once per session (or after REFRESH)
    if "video_data" not in st.session_state:
        with st.spinner("Fetching videos..."):
            try:
                video_data = asyncio.run(fetchVideoData(creds))
                st.session_state.video_data = video_data
            except Exception as e:
                st.error(f"Error fetching videos: {e}")
                st.session_state.video_data = {}

    video_data = st.session_state.video_data
    if not video_data:
        st.warning("No videos found.")
        return

    # show all videos as cards in a grid (no dropdown, no empty bars)
    videos = list(video_data.items())
    cols = st.columns(3, gap="large")

    for idx, (video_id, video_info) in enumerate(videos):
        col = cols[idx % 3]
        with col:
            st.markdown('<div class="css-card video-card">', unsafe_allow_html=True)
            if video_info.get("thumbnail_url"):
                st.image(video_info["thumbnail_url"])
            st.markdown(
                f"<div class='video-card-title'>{video_info['title']}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='video-meta'>Views: {video_info['views']} • Likes: {video_info['likes']} • Comments: {video_info['comments']}</div>",
                unsafe_allow_html=True,
            )
            if video_info.get("description"):
                st.caption(video_info["description"])
            
            # Button to trigger analysis
            if st.button("Analyze Comments", key=f"analyze_{video_id}"):
                analyze_video(creds, video_id)
            
            # Show results if this video is the one currently analyzed
            if st.session_state.get("analysis_video_id") == video_id:
                render_analysis_results(creds, video_id)
            
            st.markdown("</div>", unsafe_allow_html=True)


def analyze_video(credentials, video_id: str):
    with st.spinner("Analyzing comments... this may take a moment."):
        analysis_obj = VideoAnalysis()
        try:
            comment_itr = fetchVideoComments(credentials, video_id)

            async def consume_comments():
                async for comment_dict in comment_itr:
                    analysis_obj.appendComments(comment_dict)

            asyncio.run(consume_comments())

            if analysis_obj.comments_df.empty:
                st.warning("No comments found for this video.")
                return

            # Classify
            analysis_obj.classifyComments()
            
            # Save results to session state
            st.session_state["analysis_video_id"] = video_id
            st.session_state["analysis_obj"] = analysis_obj
            st.session_state["analysis_time"] = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Generate images immediately so they are ready
            analysis_obj.createWordCloud(video_id)
            analysis_obj.createClassificationGraph(video_id)

        except Exception as e:
            st.error(f"An error occurred: {e}")


def render_analysis_results(credentials, video_id):
    analysis_obj = st.session_state.get("analysis_obj")
    if not analysis_obj:
        return
    
    # Header with timestamp (re-analyze button removed)
    col_header = st.columns([1])[0]
    with col_header:
        time_str = st.session_state.get("analysis_time", "")
        st.success(f"Analysis complete! (Last updated: {time_str})")
        st.caption("Note: Changes made on YouTube may take a few minutes to reflect here.")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Word Cloud", "Classification", "Toxic Comments", "All Comments"]
    )

    # FIX: Use robust absolute path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    img_dir = os.path.join(project_root, "app", "static", "images")
    
    with tab1:
        img_path = os.path.join(img_dir, f"word_cloud_{video_id}.png")
        if os.path.exists(img_path):
            # Read as bytes to prevent browser caching of static file
            with open(img_path, "rb") as f:
                img_bytes = f.read()
            st.image(img_bytes, caption="Word cloud of comments")
        else:
            st.warning(f"Image not found at: {img_path}")

    with tab2:
        # Use dynamic chart instead of static image
        predictions = analysis_obj.predictions
        if not predictions.empty:
            # Calculate counts for each class (columns 1 onwards)
            class_cols = predictions.columns[1:]
            counts_data = []
            for col in class_cols:
                # Count how many rows have 1 for this class
                count = predictions[predictions[col] == 1].shape[0]
                counts_data.append({"Class": col, "Count": count})
            
            import pandas as pd
            chart_df = pd.DataFrame(counts_data).set_index("Class")
            
            st.markdown("#### Distribution of Toxic Comments")
            # don't set color param to respect streamlit's defaults
            st.bar_chart(chart_df)
        else:
            st.warning("No classification data available.")

    with tab3:
        st.subheader("Toxic Comments")

        toxic_ids = analysis_obj.getToxicIds()
        toxic_comments = analysis_obj.comments_df[
            analysis_obj.comments_df["id"].isin(toxic_ids)
        ]

        if toxic_comments.empty:
            st.success("No toxic comments found! 🎉")
            return

        st.error(f"Found {len(toxic_comments)} toxic comments.")

        # Allow selection
        toxic_comments_display = toxic_comments.copy()
        toxic_comments_display.insert(0, "Select", True)

        edited_df = st.data_editor(
            toxic_comments_display[["Select", "comment_text"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Select": st.column_config.CheckboxColumn("Select", default=True),
                "comment_text": st.column_config.TextColumn("Comment"),
            },
            key=f"editor_{video_id}",
        )

        # Get selected IDs
        selected_indices = edited_df[edited_df["Select"]].index
        selected_ids = toxic_comments.loc[selected_indices, "id"].tolist()

        col_del_sel, col_del_all = st.columns(2)

        # -------- DELETE SELECTED --------
        with col_del_sel:
            if st.button(
                f"DELETE {len(selected_ids)} SELECTED COMMENTS",
                type="primary",
                disabled=not selected_ids,
                key=f"del_sel_{video_id}",
            ):
                try:
                    # 1) Attempt to delete on YouTube
                    asyncio.run(rejectComments(credentials, selected_ids))

                    # 2) Immediately re-fetch fresh comments from YouTube & re-classify
                    new_analysis = refresh_analysis_from_youtube(credentials, video_id)

                    # 3) Use the fresh analysis in session state (and update timestamp)
                    st.session_state["analysis_obj"] = new_analysis
                    st.session_state["analysis_video_id"] = video_id
                    st.session_state["analysis_time"] = datetime.datetime.now().strftime("%H:%M:%S")

                    # 4) Update cached video_data comment count if present
                    if "video_data" in st.session_state and video_id in st.session_state["video_data"]:
                        try:
                            st.session_state["video_data"][video_id]["comments"] = len(new_analysis.comments_df)
                        except Exception:
                            pass

                    st.success("Selected comments deleted — view updated with fresh data.")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error deleting comments: {e}")

        # -------- DELETE ALL TOXIC --------
        with col_del_all:
            if st.button(
                f"DELETE ALL {len(toxic_ids)} TOXIC COMMENTS",
                key=f"del_all_{video_id}",
            ):
                try:
                    # 1) Delete on YouTube
                    asyncio.run(rejectComments(credentials, toxic_ids))

                    # 2) Immediately refresh from youtube and re-classify
                    new_analysis = refresh_analysis_from_youtube(credentials, video_id)

                    # 3) Update session state + timestamp
                    st.session_state["analysis_obj"] = new_analysis
                    st.session_state["analysis_video_id"] = video_id
                    st.session_state["analysis_time"] = datetime.datetime.now().strftime("%H:%M:%S")

                    # 4) Update cached video_data comment count if present
                    if "video_data" in st.session_state and video_id in st.session_state["video_data"]:
                        try:
                            st.session_state["video_data"][video_id]["comments"] = len(new_analysis.comments_df)
                        except Exception:
                            pass

                    st.success("All toxic comments deleted — view updated with fresh data.")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error deleting comments: {e}")


    with tab4:
        st.info(f"Total Comments Analyzed: {len(analysis_obj.comments_df)}")
        st.dataframe(
            analysis_obj.comments_df[["comment_text"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "comment_text": st.column_config.TextColumn("Comment"),
            }
        )


# ---------- ABOUT PAGE ----------


def render_about():
    st.title("About DeTox")
    st.markdown(
        """
    <div class="css-card">
        <h3>What is DeTox?</h3>
        <p>
        DeTox uses advanced Natural Language Processing to analyze comments on your YouTube
        videos in real time. We identify hate speech, harassment, threats, and other
        harmful content so you can maintain a healthy community without the manual effort.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            """
        <div class="css-card">
            <h3>🤖 AI Powered</h3>
            <p>State-of-the-art deep learning models fine-tuned on real YouTube comments.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            """
        <div class="css-card">
            <h3>⚡ Real-time</h3>
            <p>Analyze new comments as they appear and act on toxicity in seconds.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            """
        <div class="css-card">
            <h3>🔒 Secure</h3>
            <p>We use official YouTube APIs and never store your credentials on our servers.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


# ---------- STORIES PAGE ----------


def render_stories():
    st.title("Success Stories")
    st.markdown("### See what creators are saying about DeTox.")

    reviews = [
        {
            "name": "Sarah Jenkins",
            "date": "2 days ago",
            "title": "Game changer for my channel",
            "text": "I used to spend hours deleting hate comments. DeTox does it in seconds. Now I can focus on creating content.",
            "stars": "★★★★★",
        },
        {
            "name": "TechWithMike",
            "date": "1 week ago",
            "title": "Finally peace of mind",
            "text": "The accuracy is incredible. It catches things I would have missed. Highly recommended for any serious YouTuber.",
            "stars": "★★★★★",
        },
        {
            "name": "GamingPro99",
            "date": "3 days ago",
            "title": "Great tool",
            "text": "Setup was super easy. I love the dashboard view where I can see exactly what's being filtered out.",
            "stars": "★★★★☆",
        },
        {
            "name": "Jessica Vlogs",
            "date": "1 day ago",
            "title": "Saved my mental health",
            "text": "The toxicity was getting to me. DeTox cleaned it all up. It's like having a 24/7 moderator.",
            "stars": "★★★★★",
        },
    ]

    for review in reviews:
        st.markdown(
            f"""
        <div class="review-card">
            <div class="stars">
                {review['stars']} <span class="verified">✓ Verified creator</span>
            </div>
            <h3>{review['title']}</h3>
            <p>"{review['text']}"</p>
            <div style="font-size: 0.9rem; color: #374151;">
                <strong>{review['name']}</strong> • {review['date']}
            </div>
        </div>
        """,
            unsafe_allow_html=True, 
        )


# ---------- ENTRYPOINT ----------
if __name__ == "__main__":
    main()
