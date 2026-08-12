import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Initialize OpenAI client pointed to Groq's free endpoint
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)

SUMMARY_PROMPT_TEMPLATE = """
You are a helpful assistant. Summarize the following 
text into 3 concise bullet points:--
{text}--
Bullet Points:
"""

def run_summary_pipeline(input_text):
    prompt = SUMMARY_PROMPT_TEMPLATE.format(text=input_text)
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # Free fast model on Groq
        messages=[
            {"role": "system", "content": "You are a summarization assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )
    return response.choices[0].message.content
if __name__ == "__main__":
    print("Paste your text below to summarize:\n")
    user_input = input()
    output = run_summary_pipeline(user_input)
    print("\n🧠 Summary:\n", output)