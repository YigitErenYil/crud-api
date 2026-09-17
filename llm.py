import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_API_KEY"),
    timeout=30.0,
    max_retries=0,  # kendi retry mantığımızı yazacağız, SDK'nın sessiz varsayılanına güvenmiyoruz
)

if __name__ == "__main__":
    res = client.chat.completions.create(
        model=os.getenv("LLM_MODEL"),
        messages=[{"role": "user", "content": "Reply with exactly the word: ready"}],
    )
    print(res.choices[0].message.content)