from openai import OpenAI
import os

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "<your OpenAI API key if not set as env var>"))

completion = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "system", "content": "너는 대한민국에 대해 잘 아는 사람이야."},
    {"role": "user", "content": "대한민국 역대 대통령 순서를 알려줘."}
  ]
)

print(completion.choices[0].message.content)