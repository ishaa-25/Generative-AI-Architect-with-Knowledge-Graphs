import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

# 1. Setup logging and load environment variables
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()

# 2. Initialize FastAPI and Groq Client
app = FastAPI(title="GenAI Inference API", version="1.0")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 3. Define the Request Data Schema (Pydantic)
class PromptRequest(BaseModel):
    prompt: str = "Explain quantum computing in one sentence."

# 4. Root Health Check Endpoint
@app.get("/")
def health_check():
    return {"status": "healthy", "service": "GenAI API"}

# 5. Inference Generation Endpoint
@app.post("/generate")
async def generate_response(request: PromptRequest):
    try:
        logging.info(f"Incoming Prompt: {request.prompt}")
        
        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": request.prompt}]
        )
        
        answer = completion.choices[0].message.content
        logging.info(f"Generated response length: {len(answer)} chars")
        
        return {"response": answer}
        
    except Exception as e:
        logging.error(f"Error generating completion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
