from openai import OpenAI
import os, backoff
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@backoff.on_exception(backoff.expo, Exception, max_time=60)
def chat(messages, model="gpt-4.1", temperature=0.2, max_tokens=600):
    """
    Chat completion using GPT-4.1
    - Input cost: $2.00 per 1M tokens
    - Output cost: $8.00 per 1M tokens
    - Context window: 1,047,576 tokens
    - Max output: 32,768 tokens
    - Knowledge cutoff: May 31, 2024
    """
    try:
        response = client.chat.completions.create(
            model=model,  # Using GPT-4.1 - latest flagship model
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            response_format={ "type": "text" }  # Ensuring text output
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        return "I apologize, but I encountered an error. Please try again." 