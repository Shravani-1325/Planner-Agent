import os
import json
from groq import Groq
from dotenv import load_dotenv
import traceback

from tools import TOOLS_SCHEMA, AVAILABLE_FUNCTIONS

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
print("Key loaded:", bool(os.environ.get("GROQ_API_KEY")))


EXECUTOR_SYSTEM_PROMPT = """You are the execution module of an autonomous document-generation agent,
acting as a senior consultant producing a polished internal business document.

You have two tools:
- get_mock_data(topic): Use the get_mock_data tool only when numerical information is required.
  Strictly do not write the tool name in normal text. Dont mention the "get_mock_data" in the text.
  Always use the provided tool interface.
  use this to pull concrete supporting figures (budget, timeline,
  team size, growth metrics, etc.) whenever a section would benefit from real numbers
  instead of vague claims. Call it once per major topic that needs grounding.
- structure_document(title, sections): call this EXACTLY ONCE, at the very end, once
  all content is fully drafted. This is your final output -- never return plain text.

FIRST, DECIDE THE DOCUMENT'S SHAPE BASED ON THE REQUEST:

CASE A -- The request is a plan, roadmap, schedule, or learning path tied to a
duration (e.g. "learn ML in 1 month", "30-day fitness plan", "2-week onboarding"):
  - Organize the ENTIRE document by time unit. Divide the stated duration into
    clear chunks (e.g. "Week 1", "Week 2", "Week 3", "Week 4" for a 1-month plan;
    "Day 1-3" for a short sprint) and make EACH time chunk its own section.
  - Each time-unit section must state exactly which topics/tasks belong in that
    period, and MUST use concrete, checkable steps (e.g. "Learn X, practice Y,
    build Z") rather than generic prose about the subject in general.
  - Do NOT include generic essay sections like "Introduction" or "Conclusion" for
    this case -- the schedule itself IS the document. You may add one short
    "Overview" section at the top (goal + total duration) and optionally a short
    "How to use this plan" note at the end -- nothing more.

CASE B -- The request is a business document that is NOT time-bound (a proposal,
SOP, business report, technical design, etc.):
  - Build the document around the planned steps you were given, one section per
    step or logical group of steps.
  - Each section: 3-5 full paragraphs, specific numbers/examples pulled from
    get_mock_data where useful, professional tone.
  - Aim for 6-8 sections, including an Executive Summary, Risks & Mitigations,
    Timeline/Milestones, and Conclusion/Next Steps where relevant to the document
    type -- do not force irrelevant sections in.

In both cases: use concrete specifics, never vague filler. Do not return plain
text as your final answer -- your final action must always be a call to
structure_document with the fully drafted content.
"""


def execute_plan(user_request: str, plan: dict, max_turns: int = 6) -> dict:
    messages = [
        {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"User request: {user_request}\n\n"
                f"Document type: {plan.get('document_type')}\n"
                f"Assumptions made: {json.dumps(plan.get('assumptions', []))}\n"
                f"Planned steps: {json.dumps(plan.get('steps', []))}\n\n"
                "Execute these steps now and produce the final document via "
                "structure_document."
            ),
        },
    ]
    tool_call_log = []

    for _ in range(max_turns):
      response = None
      last_error = None
      
      #>> Retry Block
      for attempt in range(3):
        try:
          response = client.chat.completions.create(
              model = "llama-3.3-70b-versatile",
              messages=messages,
              tools = TOOLS_SCHEMA,
              tool_choice= "auto",
              temperature = max(0.4 - attempt * 0.15, 0.1), # getting stricter each retry
              max_tokens = 6000,
          )
          break
        except Exception as e:
          last_error = e
          error_text = str(e)
          if "tool_use_failed" in error_text or "Failed to call a function" in error_text:
            messages.append(
              {
                "role" : "user",
                "content" : (
                  "Your last attempt tried to write a tool call as plain text (e.g. <function=...>), which is invalid."
                  "Do NOT write function calls as text."
                  "Use the actual tool-calling mechanism to call get_mock_data or structure_document"
                ),
              }
              
            )
          continue
        
      if response is None:
        return {
          "title" : str(plan.get("document_type", "Generated Document")).title(),
          "sections": [
            {
              "heading" : "Summary",
              "content" : (
                "The agent's model provider returned repeated errors while"
                f"generating this document ({last_error}). Please try again"
              ),
            }
          ],
          "tool_calls": tool_call_log,
        }        
      msg = response.choices[0].message
      print("\n" + "="*80)
      print("RAW LLM RESPONSE")
      print(msg.model_dump())
      print("="*80 + "\n")
      messages.append(msg)
        
      if not msg.tool_calls:
          messages.append(
            {
              "role" : "user",
              "content" : "Please call structure_document now with your final content"
            }
          )
          continue
        
        
      for tool_call in msg.tool_calls:
          print("\nTool Name:", tool_call.function.name)
          print("Arguments:", tool_call.function.arguments)
          
          fn_name = tool_call.function.name
          fn_args = json.loads(tool_call.function.arguments)
          tool_call_log.append({"tool":fn_name, "args": fn_args})
          
          if fn_name == "structure_document":
              return {
                  "title" : fn_args.get("title", "Generated Document"),
                  "sections" : fn_args.get("sections", []),
                  "tool_calls" : tool_call_log,
              }
                
          fn = AVAILABLE_FUNCTIONS.get(fn_name)
          result = fn(**fn_args) if fn else {"error": f"Unknown tool: {fn_name}"}
            
          messages.append({
              "role" : "tool",
              "tool_call_id" : tool_call.id,
              "name" : fn_name,
              "content": json.dumps(result),
          })
            
    return{
        "title" : str(plan.get("document_type", "Generated Document")).title(),
        "sections" : [
          {
            "heading" : "Summary", 
            "content" : "The agent reached its turn limit before finalizing structured content. This is safety cap, not crash."
          }
        ],
        "tool_calls" : tool_call_log,
        
    }
    

            
            



