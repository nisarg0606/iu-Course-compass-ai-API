# utils.py
import json
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from fastapi import HTTPException

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
mongo_client = MongoClient(os.getenv("MONGO_URI"))
mongo_db = mongo_client[os.getenv("MONGO_DB_NAME")]
chat_history = []

# Load courses.json once
with open("courses.json", "r") as f:
    catalog = json.load(f)
courses = catalog["courses"]

# Summarize one course
def summarize_course(course):
    return (
        f"Course Name: {course['name']}\n"
        f"Code: {course['code']}\n"
        f"Credits: {course['credits']}\n"
        f"Department: {course['department']} ({course['departmentCode']})\n"
        f"Term: {course['term']} {course['year']}\n"
        f"Schedule: {', '.join(course['schedule']['days'])} {course['schedule']['startTime']}-{course['schedule']['endTime']}\n"
        f"Mode: {course['mode']}\n"
        f"Location: {course['location']}\n"
        f"Availability: {course['availability']['enrolled']}/{course['availability']['total']} enrolled\n"
        f"Professor: {course['professor']}\n"
        f"Prerequisites: {', '.join(course.get('prerequisites', [])) or 'None'}\n"
        f"Textbooks: {', '.join(course.get('textbooks', [])) or 'None'}\n"
        f"Description: {course['description']}\n"
    )

# Full context for Gemini prompt
COURSE_CONTEXT = "\n---\n".join(summarize_course(c) for c in courses)

# Gemini response function
def get_gemini_response(user_query):
    model = genai.GenerativeModel("gemini-2.0-flash")

    global chat_history

    system_prompt = (
        "You are a university course advisor AI. Your job is to help students pick suitable courses based on their interests, goals, and the course catalog below. "
        "You must only recommend courses from the provided list and explain your reasoning.\n\n"
        "Here is the course catalog:\n\n" + COURSE_CONTEXT +
        "Do not give me any text in bold and also do not use any markdown formatting. Do not give any additional information or context outside of the course catalog provided."
        "if you ever need to mention the professor data in the output. only mention the professor's name and do not mention id, rating, department, email or avgRating."
        "if there are less seats in the course automatically recommend the next best similar course available in the catalog saying that since the seats are limited in the course you asked for, I am recommending the next best similar course available. "
        "Only respond with the course recommendations and explanations based on the user's query and give me the reponse strictly in html format only. Do not add any ticks (`) or code blocks (```), and do not use any markdown formatting."
        """
        "<html>\n"
        "<body>\n"
        "[Your response content here]\n"
        "</body>\n"
        "</html>\n"
        """
    )

    if not chat_history:
        chat_history.append({"role": "user", "parts": [system_prompt]})

    # Add current query
    chat_history.append({"role": "user", "parts": [user_query]})

    # Call Gemini with full chat
    response = model.generate_content(chat_history)
    reply = response.text

    # Add model response
    chat_history.append({"role": "model", "parts": [reply]})

    # Optionally truncate to last 20 entries
    chat_history = chat_history[-40:]

    return reply


def hash_password(password):
    return generate_password_hash(password)

def user_signup(username, password):
    """
    Sign up a new user by storing their credentials in the database.

    Args:
        username (str): The username of the user.
        password (str): The password of the user.

    Returns:
        str: A success message if signup is successful, or an error message if the username is already taken.
    """
    users_collection = get_collection("users")

    # Check if the username already exists
    if users_collection.find_one({"username": username}):
        return "Error: Username already exists."

    # Hash the password and store the user in the database
    hashed_password = generate_password_hash(password)
    users_collection.insert_one({"username": username, "password": hashed_password})
    return f"User '{username}' signed up successfully."

def user_sign_in(username, password):
    """
    Sign in a user by creating a session.

    Args:
        username (str): The username of the user.
        password (str): The password of the user.

    Returns:
        str: A success message indicating the user has signed in.
    """
    # check the user in db and if exists then create a session
    users_collection = get_collection("users")
    # user_sessions_collection = get_collection("user_sessions")

    # Check if the user is already logged in
    # if user_sessions_collection.find_one({"username": username}):
    #     return "Error: User already logged in."

    # Check if the user exists in the database
    user = users_collection.find_one({"username": username})
    if not user:
        return "Error: User does not exist."

    # Validate the password
    if not check_password_hash(user["password"], password):
        return "Error: Invalid password."

    # Create a session for the user
    # user_sessions_collection.update_one(
    #     {"username": username},
    #     {"$set": {"username": username, "signed_in": True}},
    #     upsert=True
    # )
    return f"User '{username}' logged in successfully."
    

def user_sign_out(username):
    """
    Sign out a user by removing their session.

    Args:
        username (str): The username of the user.

    Returns:
        str: A success message if sign-out is successful, or an error message if the user is not signed in.
    """
    user_sessions_collection = get_collection("user_sessions")

    # Check if the user is logged in
    result = user_sessions_collection.delete_one({"username": username})
    if result.deleted_count > 0:
        return f"User '{username}' logged out successfully."
    else:
        return "Error: User is not logged in."
    
    
def is_user_logged_in(username):
    """
    Check if a user is currently logged in.

    Args:
        username (str): The username of the user.

    Returns:
        bool: True if the user is logged in, False otherwise.
    """
    user_sessions_collection = get_collection("user_sessions")
    return user_sessions_collection.find_one({"username": username})
    
def get_collection(collection_name):
    """
    Get a MongoDB collection.

    Args:
        collection_name (str): The name of the collection to retrieve.

    Returns:
        pymongo.collection.Collection: The requested collection.
    """
    return mongo_db[collection_name]

def sanitize_course_data(courses):
    for course in courses:
        course["credits"] = int(course["credits"])
        course["year"] = int(course["year"])
        for k in ["overall", "difficulty", "workload", "organization"]:
            course["ocq"][k] = float(course["ocq"][k])
        for comment in course["ocq"]["comments"]:
            comment["rating"] = int(comment["rating"])
        for k in ["A", "B", "C", "D", "F", "Withdraw"]:
            course["gradeDistribution"][k] = int(course["gradeDistribution"][k])
    return courses

# I want a function to recommend a course from the course catalog based on a user's career goal and subject which will be mandatorily provided by the user and optional parameters enrolment type and available days through the gemini api
def gemini_recommend_course(career_goal: str, subject: str, enrollment_type: str = None, available_days: list = None):
    model = genai.GenerativeModel("gemini-2.0-flash")

    system_prompt = """
    You are an academic course recommendation AI for Indiana University.

    Recommend multiple courses based on the user's career goal and subject of interest. For each course, respond in the **exact JSON format** below and wrap multiple course objects in a single JSON array. No explanation or surrounding text.

    Use this exact structure:

    [
    {
        "id": "course_id",
        "name": "Course Name",
        "code": "DEPT-CODE",
        "department": "Department Name",
        "departmentCode": "DEPT",
        "number": "Course Number",
        "credits": 3,
        "term": "Fall",
        "year": 2024,
        "description": "Course description here.",
        "professor": {
        "id": "p1",
        "name": "Dr. Professor Name",
        "department": "Department Name",
        "email": "email@university.edu",
        "avgRating": 4.5
        },
        "location": "Building Room",
        "schedule": {
        "days": ["Monday", "Wednesday"],
        "startTime": "10:00",
        "endTime": "11:15"
        },
        "mode": "Online",
        "availability": {
        "total": 60,
        "enrolled": 42
        },
        "prerequisites": ["COURSE-101"],
        "textbooks": ["Textbook Title Here"],
        "ocq": {
        "overall": 4.2,
        "difficulty": 3.0,
        "workload": 3,
        "organization": 4,
        "comments": [
            {
            "text": "Comment here.",
            "date": "2024-10-01",
            "rating": 4
            }
        ]
        },
        "gradeDistribution": {
        "A": 20,
        "B": 15,
        "C": 5,
        "D": 2,
        "F": 1,
        "Withdraw": 3
        }
    }
    ]

    Return a JSON array of such course objects **only**, no explanation or surrounding text.
    """

    query = (
        f"{system_prompt}\n\n"
        f"Career Goal: {career_goal}\n"
        f"Subject: {subject}\n"
    )
    if enrollment_type:
        query += f"Enrollment Type: {enrollment_type}\n"
    if available_days:
        query += f"Available Days: {', '.join(available_days)}\n"

    try:
        response = model.generate_content(query)
        raw_text = response.text.strip()

        # Debug log raw Gemini response
        # print("\nRAW GEMINI RESPONSE:\n", raw_text)

        # Extract JSON array
        json_match = re.search(r"\[.*\]", raw_text, re.DOTALL)
        if not json_match:
            raise HTTPException(status_code=500, detail="JSON array not found in Gemini response.")

        raw_json = json_match.group()
        parsed_data = json.loads(raw_json)

        # Confirm it's a list
        if not isinstance(parsed_data, list):
            raise HTTPException(status_code=500, detail="Extracted content is not a list.")

        required_fields = {"id", "name", "code", "schedule", "credits"}
        for course in parsed_data:
            if not required_fields.issubset(course.keys()):
                # print("Missing fields in:", course)
                raise HTTPException(status_code=500, detail="One or more course objects are missing required fields.")

        return parsed_data

    except json.JSONDecodeError as e:
        # print("\nJSON decode error:\n", str(e))
        # print("\nRAW JSON THAT FAILED:\n", raw_json if 'raw_json' in locals() else raw_text)
        raise HTTPException(status_code=500, detail="Extracted Gemini JSON is invalid.")
    except Exception as e:
        # print("\nException caught:\n", str(e))
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")