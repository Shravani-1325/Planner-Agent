import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
model = "llama-3.3-70b-versatile"
client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

PLANNER_SYSTEM_PROMPT = '''
Given a user's natural language request, decide:
1. What TYPE of business document best satisfies it (e.g. proposal, meeting minutes,
   project plan, business report, technical design, SOP, product specification).
2. A short ordered list of concrete steps needed to research, draft, and finalize
   that document.

If the request is ambiguous, missing details, or conflicting, make REASONABLE
assumptions and state them as a step (e.g. "Assume a mid-size B2B SaaS company
since no industry was specified").

Respond with ONLY valid JSON, no markdown fences, no commentary, in this exact shape:
{
  "document_type": "string",
  "assumptions": ["string", ...],
  "steps": [
    {"step": 1, "action": "string"},
    {"step": 2, "action": "string"}
  ]
}
'''
def create_plan(user_request : str) -> dict:
    response = client.chat.completions.create(
        model = model,
        messages=[
            {"role" : "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_request}
        ],
        temperature = 0.3,        
    )
    
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        plan = json.loads(raw)
        if "steps" not in plan or not isinstance(plan["steps"], list):
            raise ValueError("Plan missing valid 'steps' list")
        return plan
    except (json.JSONDecodeError, ValueError):
        return { 
                "document_type": "bussiness_report",
                "assumptions": ["Planner output was malformed; using a generic fallback plan"],
                "steps": [
                    {"step": 1, "action": "Gather revelant information for the request"},
                    {"step": 2, "action": "Draft structured content across logical sections"},
                    {"step": 3, "action": "Finalize and structure the document"},
                ],
            }