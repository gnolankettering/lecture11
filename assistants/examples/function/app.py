import json
import os
import time

from openai import OpenAI
import config


def show_json(obj):
    print(json.loads(obj.model_dump_json()))


client = OpenAI(
    api_key=(config.OPENAI_API_KEY),
)

# fake answers for multiple choice
def get_mock_response_from_user_multiple_choice():
    return "a"

# fake answers for free text response
def get_mock_response_from_user_free_response():
    return "I don't know."

# define quiz
def display_quiz(title, questions):
    print("Quiz:", title)
    print()
    responses = []

    for q in questions:
        print(q["question_text"])
        response = ""

        # If multiple choice, print options
        if q["question_type"] == "MULTIPLE_CHOICE":
            for i, choice in enumerate(q["choices"]):
                print(f"{i}. {choice}")
            response = get_mock_response_from_user_multiple_choice()

        # Otherwise, just get response
        elif q["question_type"] == "FREE_RESPONSE":
            response = get_mock_response_from_user_free_response()

        responses.append(response)
        print()

    return responses

# give ChatGPT an example quiz 
responses = display_quiz(
    "Sample Quiz",
    [
        {"question_text": "What is your name?", "question_type": "FREE_RESPONSE"},
        {
            "question_text": "What is your favorite color?",
            "question_type": "MULTIPLE_CHOICE",
            "choices": ["Red", "Blue", "Green", "Yellow"],
        },
    ],
)
print("Responses:", responses)

# define the function using ChatGPT's function template
function_json = {
    "name": "display_quiz",
    "description": "Displays a quiz to the student, and returns the student's response. A single quiz can have "
                   "multiple questions.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "questions": {
                "type": "array",
                "description": "An array of questions, each with a title and potentially options (if multiple choice).",
                "items": {
                    "type": "object",
                    "properties": {
                        "question_text": {"type": "string"},
                        "question_type": {
                            "type": "string",
                            "enum": ["MULTIPLE_CHOICE", "FREE_RESPONSE"],
                        },
                        "choices": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["question_text"],
                },
            },
        },
        "required": ["title", "questions"],
    },
}

# create Assistant - with code_interpreter, retrieval and function tools turned on, passing in the function definition
# you can also create the function in playground and pass in the Assistant ID later
assistant = client.beta.assistants.create(
    name="function calling assistant",
    instructions="You are an expert in function calling and extracting information.",
    tools=[
        {"type": "code_interpreter"},
        {"type": "function", "function": function_json},
    ],
    model="gpt-4-1106-preview",
)

#submit the message to the assistant
def submit_message(assistant_id, thread, user_message):
    client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=user_message
    )
    return client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

#create a thread and run the assistant
def create_thread_and_run(user_input):
    thread = client.beta.threads.create()
    run = submit_message(assistant.id, thread, user_input)
    return thread, run


def pretty_print(messages):
    print("# Messages")
    for m in messages:
        print(f"{m.role}: {m.content[0].text.value}")
    print()


# Waiting in a loop
def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

# start the thread and run the assistant
thread, run = create_thread_and_run(
    "Make a quiz with 2 questions: One open ended, one multiple choice. Then, give me feedback for the responses."
)
run = wait_on_run(run, thread)
run.status

# Extract single tool call
tool_call = run.required_action.submit_tool_outputs.tool_calls[0]
name = tool_call.function.name
arguments = json.loads(tool_call.function.arguments)

print("Function Name:", name)
print("Function Arguments:", arguments)

responses = display_quiz(arguments["title"], arguments["questions"])
print("Responses:", responses)

run = client.beta.threads.runs.submit_tool_outputs(
    thread_id=thread.id,
    run_id=run.id,
    tool_outputs=[
        {
            "tool_call_id": tool_call.id,
            "output": json.dumps(responses),
        }
    ],
)
show_json(run)


