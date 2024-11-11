
from openai import OpenAI

import config 

client = OpenAI(api_key=config.OPENAI_API_KEY)

question = input("Ask me anything: ")

response = client.chat.completions.create(
  messages=[
    {
      "role": "user",
      "content": question
    }
  ],
  model="ft:gpt-3.5-turbo-0125:kettering-university-computer-science::ASA7UpRv",
  temperature=0,
  max_tokens=1024,
  n=1,
  stop=None
)

print(response.choices[0].message.content)

