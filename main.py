# main.py
from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from utils import gemini_recommend_course, get_gemini_response, catalog, user_sign_in, user_sign_out, user_signup, course_recommendation

app = FastAPI()

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request body model for chat
class QueryRequest(BaseModel):
    query: str

# Request body model for sign-in
class SignInRequest(BaseModel):
    username: str
    password: str

# Request body model for sign-out
class SignOutRequest(BaseModel):
    username: str  # Only username is required for sign-out

class RecommendationRequest(BaseModel):
    career_goal: str
    subject: str
    enrollment_type: Optional[str] = None  # Optional field for enrollment type
    available_days: Optional[List[str]] = None  # Optional field for available days

# Chat endpoint
@app.post("/chat")
async def chat(request: QueryRequest):
    try:
        reply = get_gemini_response(request.query)
        return {"response": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/courses")
async def get_courses():
    return catalog

# GET /health - Simple health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Course Selector API is running"}

@app.post("/signup")
async def sign_up(username: str = Form(...), password: str = Form(...)):
    """
    Sign up a new user using form data.
    """
    try:
        message = user_signup(username, password)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST /signin - User sign-in
@app.post("/signin")
async def sign_in(username: str = Form(...), password: str = Form(...)):
    """
    Sign in a user using form data.
    """
    try:
        message = user_sign_in(username, password)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST /signout - User sign-out
@app.post("/signout")
async def sign_out(username: str = Form(...)):
    """
    Sign out a user using form data.
    """
    try:
        message = user_sign_out(username)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
#give me the endpoint to get recommendation from the model based on user query and chat history use the recommend_course function from utils.py
@app.post("/recommendations")
async def get_recommendations(request: RecommendationRequest):
    """
    Get course recommendations from the Gemini model based on the user's career goal, subject, and preferences.
    """
    try:
        # Call the gemini_recommend_course function from utils.py
        recommendations = gemini_recommend_course(
            career_goal=request.career_goal,
            subject=request.subject,
            enrollment_type=request.enrollment_type,
            available_days=request.available_days
        )
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/course_rec")
async def get_recommendations():
    """
    Call recommendation()
    """
    try:
        recommendations = course_recommendation()
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        