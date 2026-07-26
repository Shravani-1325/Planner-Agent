from dotenv import load_dotenv
load_dotenv()
import os
from groq import Groq

client  = Groq(api_key=os.environ["GROQ_API_KEY"])

resp = client.chat.completions.create(
    model = "llama-3.3-70b-versatile",
    messages = [{"role": "user", "content": "Say hello in one word"}]
    
)
print(resp.choices[0].message.content)