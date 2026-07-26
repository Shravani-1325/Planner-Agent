import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from planner import create_plan
from executor import execute_plan
from doc_generator import generate_docx


app = FastAPI(title= "Autonomous Document Agent", version= "1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods=["*"],
    allow_headers = ["*"],
)

class AgentRequest(BaseModel): #template
    #>> Input data must have a key named request
    request: str = Field(
        ..., min_length=3, description="Natural Language request describing the document to produce"
    )

@app.post("/agent")
def run_agent(payload: AgentRequest):
    user_request = payload.request.strip()
    
    if not user_request:
        raise HTTPException(status_code = 400, detail = "Request cannot be empty")
    
    try:
        plan = create_plan(user_request)
    except Exception as e:
        raise HTTPException(status_code=502, detail = f"Planning step Failed: {e}") # Bad Gateway
    
    try:
        result = execute_plan(user_request, plan)
    except Exception as e:
        raise HTTPException(status_code= 502, detail = f"Excecution step failed : {e}")
    
    try:
        filepath = generate_docx(result["title"], result["sections"])
    except Exception as e:
        raise HTTPException(status_code=500, detail = f"Document generation failed: {e}") # Internal Server Error

    
    return {
        "request" : user_request,
        "plan": plan,
        "tool_calls" : result.get("tool_calls",[]),
        "document_title": filepath,
        "download_url" : f"/download/{os.path.basename(filepath)}",
    }
    
@app.get("/download/{filename}")
def download_document(filename: str):
    filepath = os.path.join("output", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail = "File not Found")
    return FileResponse(
        filepath,
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )
    
@app.get("/")
def root():
    return {"status": "ok", "message":"POST a request to /agent to generate a document"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host ="0.0.0.0", port = 8000)