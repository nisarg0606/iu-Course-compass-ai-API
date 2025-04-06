# utils.py
import json
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
mongo_client = MongoClient(os.getenv("MONGO_URI"))
mongo_db = mongo_client[os.getenv("MONGO_DB_NAME")]

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
def get_gemini_response(user_query, chat_history=None):
    model = genai.GenerativeModel("gemini-2.0-flash")

    system_prompt = (
        "You are a university course advisor AI. Your job is to help students pick suitable courses based on their interests, goals, and the course catalog below. "
        "You must only recommend courses from the provided list and explain your reasoning.\n\n"
        "Here is the course catalog:\n\n" + COURSE_CONTEXT +
        "Do not give me any text in bold and also do not use any markdown formatting. Do not give any additional information or context outside of the course catalog provided."
        "Only respond with the course recommendations and explanations based on the user's query and give me the reponse strictly in html format only. Do not add any ticks (`) or code blocks (```), and do not use any markdown formatting."
        """
        "<html>\n"
        "<body>\n"
        "[Your response content here]\n"
        "</body>\n"
        "</html>\n"
        """
    )

    contents = [{"role": "user", "parts": [system_prompt]}]

    if chat_history:
        contents.extend(chat_history)

    contents.append({"role": "user", "parts": [user_query]})

    response = model.generate_content(contents)
    return response.text


user_sessions = {}

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

# I want a function to recommend a course from the course catalog based on a user's career goal and subject which will be mandatorily provided by the user and optional parameters enrolment type and available days through the gemini api
def gemini_recommend_course(career_goal: str, subject: str, enrollment_type: str = None, available_days: list = None):
    model = genai.GenerativeModel("gemini-2.0-flash")

    system_prompt = (
    """
    Recommend a course based on the user's career goal and subject.

    Args:
        career_goal (str): The user's career goal.
        subject (str): The subject of interest.
        enrollment_type (str, optional): Preferred enrollment type (e.g., "online", "in-person").
        available_days (list, optional): Preferred days of the week for classes.

    Returns:
        str: Recommended course details or a message if no suitable course is found.
    give me the response strictly in the below JSON format only:
    {
        "mode": "online" or "in-person" or "hybrid",
        "term": "Fall" or "Spring" or "Summer",
        "code": "CS101",
        "name": "Introduction to Computer Science",
        "professor": "Dr. Smith",
        "schedule" : { "days": ["Monday"], "startTime": "09:00", "endTime": "10:30" },
        "credits": 3,
        "description": "An introduction to the fundamentals of computer science, including programming, algorithms, and data structures.",
    }
    """
    )
    query = f"'{system_prompt} 'Recommend two courses for someone whose career goal is '{career_goal}' and is interested in '{subject}'. Give me the response strictly in the JSON format mentioned above even if there are multiple courses recommended. "
    
    if enrollment_type:
        query += f" Prefer {enrollment_type} enrollment."
    
    if available_days:
        query += f" Available on {', '.join(available_days)}."

    # Call Gemini API to get the response
    response = model.generate_content(query)
    json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
    if not json_match:
        raise ValueError("Gemini response did not contain valid JSON.")

    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print("Raw Gemini response:\n", response.text)
        raise ValueError("Extracted Gemini JSON is invalid.")