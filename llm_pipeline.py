import os
import openai
from dotenv import load_dotenv
# Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
# Template with placeholder
SUMMARY_PROMPT_TEMPLATE = """
You are a helpful assistant. Summarize the following 
text into 3 concise bullet points:--
{text}--
Bullet Points:
"""
def run_summary_pipeline(input_text):
    # Inject user input into the prompt
    prompt = SUMMARY_PROMPT_TEMPLATE.format(text=input_text)
    # Call OpenAI's completion endpoint (GPT-3.5 or GPT-4)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # You can use "gpt-4" if you have access
        messages=[
            {"role": "system", "content": "You are a summarization assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
         max_tokens=300
    )
    return response['choices'][0]['message']['content']
if __name__ == "__main__":
    print("Paste your text below to summarize:\n")
    user_input = input()
    output = run_summary_pipeline(user_input)
    print("\n🧠Summary:\n", output)