import config
import os
import time
from openai import OpenAI

client = OpenAI(
  api_key=config.OPENAI_API_KEY,
)

# # Upload the file
# file = client.files.create(
#     file=open(
#         "C:\\Users\\admin\\Downloads\\kettering\\lecture11\\assistants\\examples\\files\\2023q3-alphabet-earnings-release.pdf",
#         "rb",
#     ),
#     purpose="assistants",
# )

#create assistant
assistant = client.beta.assistants.create(
    name="Document Analyst",
    instructions="You are an expert in extracting information from documents.",
    tools=[{"type": "code_interpreter"},{"type": "file_search"}],
    model="gpt-4-turbo-preview",
)

# Create a vector store caled "Financial Statements"
vector_store = client.beta.vector_stores.create(name="Financial Statements")
 
# Ready the files for upload to OpenAI
file_paths = ["2023q3-alphabet-earnings-release.pdf"]
file_streams = [open(path, "rb") for path in file_paths]
 
# Use the upload and poll SDK helper to upload the files, add them to the vector store,
# and poll the status of the file batch for completion.
file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
  vector_store_id=vector_store.id, files=file_streams
)

assistant = client.beta.assistants.update(
  assistant_id=assistant.id,
  tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
) 


# Create a thread
thread = client.beta.threads.create()

# Create a message on a thread
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Using only the attached file what were the revenues for 2022?",
)

# run and poll the assistant
run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id,
    assistant_id=assistant.id,
)


if run.status == "completed":
    messages = client.beta.threads.messages.list(thread_id=thread.id)

    print("messages: ")
    for message in messages:
        assert message.content[0].type == "text"
        print({"role": message.role, "message": message.content[0].text.value})

    client.beta.assistants.delete(assistant.id)
