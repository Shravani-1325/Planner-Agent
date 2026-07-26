import random

# Tool definitions for the autonomous agent.
'''
1. get_mock_data(topic)      -> simulates fetching real-world supporting data
2. structure_document(...)   -> the LLM's structured, final output (instead of
                                 us trying to regex/parse free-form text)

Using a tool call for the FINAL output (instead of asking the model to "return
JSON" in plain text) is the key reliability win: tool-call arguments are
schema-validated by the API, so we never have to deal with the model wrapping
JSON in markdown fences, adding commentary, or producing malformed JSON.
'''

#>> MOCK FUNCTION 
def get_mock_data(topic: str) -> dict:
    #Simulates feteching real-world data/statistics relevant to topic
    
    sample_metrics = {
        "estimated_budget" : f"${random.randint(20,500)}K",
        "growth_rate" : f"{random.randint(5,40)}%",
        "estimated_timeline": f"{random.randint(2, 16)} weeks",
        "team_size" : random.randint(3,15),
        "total_steps" : f"{random.randint(4,12)} steps",
        "confidence_level" : random.choice(["High", "Medium", "Medium-High"]),
    }
    
    return {"topic": topic, "mock_metrics": sample_metrics}


# JSON schema describing the tools for the LLM (OpenAI, Groq)
TOOLS_SCHEMA = [
    { 
        "type": "function",
        "function": {
            "name": "get_mock_data",
            "description": (
                "Fetch supporting data/statistics (simulated) for the topic, so the document is grounded in concrete numbers rather than vague claims. "
                "Call this whenever a section would benefit from specific figures."            
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic to fetch supporting data for", 
                    }
                },
                "required": ["topic"],
            },
        },
    },  
    {
        "type": "function",
        "function": {
            "name": "structure_document",
            "description": (
                "Submit the FINAL structured content for the documents. "
                "Call this exactly once after you have gathered any data you need, with the complete title and all sections."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "sections": {
                        "type": "array",
                        "description": "Ordered list of document sections",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["heading", "content"],
                        },
                    },
                },
                "required": ["title", "sections"],
            },   
        }
    }
]

# mapping of callable tool implementation(structure document is handled specially) in executor.py since iit terminates the loop, so its not listed here
AVAILABLE_FUNCTIONS = {
    "get_mock_data": get_mock_data,
}