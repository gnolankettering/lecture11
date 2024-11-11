import config
import json
from openai import OpenAI
client = OpenAI(api_key=config.OPENAI_API_KEY)

GPT_MODEL = 'gpt-4-turbo'


# The tools our customer service LLM will use to communicate
tools = [
{
  "type": "function",
  "function": {
    "name": "speak_to_user",
    "description": "Use this to speak to the user to give them information and to ask for anything required for their case.",
    "parameters": {
      "type": "object",
      "properties": {
        "message": {
          "type": "string",
          "description": "Text of message to send to user. Can cover multiple topics."
        }
      },
      "required": ["message"]
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "get_instructions",
    "description": "Used to get instructions to deal with the user's problem.",
    "parameters": {
      "type": "object",
      "properties": {
        "problem": {
          "type": "string",
          "enum": ["fraud","refund","information"],
          "description": """The type of problem the customer has. Can be one of:
          - fraud: Required to report and resolve fraud.
          - refund: Required to submit a refund request.
          - information: Used for any other informational queries."""
        }
      },
      "required": [
        "problem"
      ]
    }
  }
}
]

# Example instructions that the customer service assistant can consult for relevant customer problems
INSTRUCTIONS = [ {"type": "fraud",
                  "instructions": """• Ask the customer to describe the fraudulent activity, including the the date and items involved in the suspected fraud.
• Offer the customer a refund.
• Report the fraud to the security team for further investigation.
• Thank the customer for contacting support and invite them to reach out with any future queries."""},
                {"type": "refund",
                 "instructions": """• Confirm the customer's purchase details and verify the transaction in the system.
• Check the company's refund policy to ensure the request meets the criteria.
• Ask the customer to provide a reason for the refund.
• Submit the refund request to the accounting department.
• Inform the customer of the expected time frame for the refund processing.
• Thank the customer for contacting support and invite them to reach out with any future queries."""},
                {"type": "information",
                 "instructions": """• Greet the customer and ask how you can assist them today.
• Listen carefully to the customer's query and clarify if necessary.
• Provide accurate and clear information based on the customer's questions.
• Offer to assist with any additional questions or provide further details if needed.
• Ensure the customer is satisfied with the information provided.
• Thank the customer for contacting support and invite them to reach out with any future queries.""" }]

assistant_system_prompt = """You are a customer service assistant. Your role is to answer user questions politely and competently.
You should follow these instructions to solve the case:
- Understand their problem and get the relevant instructions.
- Follow the instructions to solve the customer's problem. Get their confirmation before performing a permanent operation like a refund or similar.
- Help them with any other problems or close the case.

Only call a tool once in a single message.
If you need to fetch a piece of information from a system or document that you don't have access to, give a clear, confident answer with some dummy values."""

def submit_user_message(user_query,conversation_messages=[]):
    """Message handling function which loops through tool calls until it reaches one that requires a response.
    Once it receives respond=True it returns the conversation_messages to the user."""

    # Initiate a respond object. This will be set to True by our functions when a response is required
    respond = False
    
    user_message = {"role":"user","content": user_query}
    conversation_messages.append(user_message)

    print(f"User: {user_query}")

    while respond is False:

        # Build a transient messages object to add the conversation messages to
        messages = [
            {
                "role": "system",
                "content": assistant_system_prompt
            }
        ]

        # Add the conversation messages to our messages call to the API
        [messages.append(x) for x in conversation_messages]

        # Make the ChatCompletion call with tool_choice='required' so we can guarantee tools will be used
        response = client.chat.completions.create(model=GPT_MODEL
                                                  ,messages=messages
                                                  ,temperature=0
                                                  ,tools=tools
                                                  ,tool_choice='required'
                                                 )

        conversation_messages.append(response.choices[0].message)

        # Execute the function and get an updated conversation_messages object back
        # If it doesn't require a response, it will ask the assistant again. 
        # If not the results are returned to the user.
        respond, conversation_messages = execute_function(response.choices[0].message,conversation_messages)
    
    return conversation_messages

def execute_function(function_calls,messages):
    """Wrapper function to execute the tool calls"""

    for function_call in function_calls.tool_calls:
    
        function_id = function_call.id
        function_name = function_call.function.name
        print(f"Calling function {function_name}")
        function_arguments = json.loads(function_call.function.arguments)
    
        if function_name == 'get_instructions':

            respond = False
    
            instruction_name = function_arguments['problem']
            instructions = INSTRUCTIONS['type' == instruction_name]
    
            messages.append(
                                {
                                    "tool_call_id": function_id,
                                    "role": "tool",
                                    "name": function_name,
                                    "content": instructions['instructions'],
                                }
                            )
    
        elif function_name != 'get_instructions':

            respond = True
    
            messages.append(
                                {
                                    "tool_call_id": function_id,
                                    "role": "tool",
                                    "name": function_name,
                                    "content": function_arguments['message'],
                                }
                            )
    
            print(f"Assistant: {function_arguments['message']}")
    
    return (respond, messages)
    

responses = submit_user_message("Hi, I have had an item stolen that was supposed to be delivered to me yesterday.")
print(responses.choices[0].message.content)