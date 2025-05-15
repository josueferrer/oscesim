import os, openai, backoff
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

@backoff.on_exception(backoff.expo, openai.error.RateLimitError, max_time=60)
def chat(messages, model="gpt-4o-mini", temperature=0.2, max_tokens=600):
    return openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    ).choices[0].message.content