# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from utils import get_gemini_response, catalog, user_sign_in, user_sign_out

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
    history: Optional[List[Dict[str, Any]]] = None

# Request body model for sign-in
class SignInRequest(BaseModel):
    username: str
    password: str

# Request body model for sign-out
class SignOutRequest(BaseModel):
    username: str  # Only username is required for sign-out

# Chat endpoint
@app.post("/chat")
async def chat(request: QueryRequest):
    try:
        reply = get_gemini_response(request.query, request.history)
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

# POST /signin - User sign-in
@app.post("/signin")
async def sign_in(request: SignInRequest):
    try:
        message = user_sign_in(request.username, request.password)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST /signout - User sign-out
@app.post("/signout")
async def sign_out(request: SignOutRequest):
    try:
        message = user_sign_out(request.username)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))