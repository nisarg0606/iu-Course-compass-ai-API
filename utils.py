# utils.py
import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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
        "Only respond with the course recommendations and explanations based on the user's query and give me the reponse strictly in html format only."
    )

    contents = [{"role": "user", "parts": [system_prompt]}]

    if chat_history:
        contents.extend(chat_history)

    contents.append({"role": "user", "parts": [user_query]})

    response = model.generate_content(contents)
    return response.text
