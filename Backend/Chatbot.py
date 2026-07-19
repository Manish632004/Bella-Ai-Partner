from groq import Groq     #  Importing the Groq library to use its API.
from json import load, dump    # Importing functions to read and write JSON files.
import datetime    # Importing the datetime module for real-time date and time information.
from dotenv import dotenv_values    # Importing dotenv_values to read environment variables from a .env file.
from Backend.Memory import get_all_facts, extract_facts_async
import cohere
import requests

# Load environment variables from the .env file.
env_vars= dotenv_values(".env")

# Retrieve specific environment variables for username, assistant name, and API key.
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey = env_vars.get("GroqAPIKey")
CohereAPIKey = env_vars.get("CohereAPIKey")

# Initialize the Groq client using the provided API key.
client = Groq (api_key=GroqAPIKey)

# Initialize an empty list to store chat messages.
messages = [ ]

def call_cohere_chat(messages, system_prompt, query):
    try:
        co = cohere.Client(api_key=CohereAPIKey)
        cohere_history = []
        for msg in messages[:-1]:
            role = "USER" if msg["role"] == "user" else "CHATBOT"
            if msg["role"] == "system":
                continue
            cohere_history.append({"role": role, "message": msg["content"]})
            
        response = co.chat(
            model="command-r-plus-08-2024",
            message=query,
            preamble=system_prompt,
            chat_history=cohere_history,
            temperature=0.7
        )
        return response.text
    except Exception as e:
        print(f"Error in Cohere Fallback: {e}")
        return None

def call_ollama_chat(messages, system_prompt):
    url = "http://localhost:11434/v1/chat/completions"
    formatted_messages = [{"role": "system", "content": system_prompt}] + messages
    payload = {
        "model": "llama3",
        "messages": formatted_messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        pass
    return None

def call_offline_fallback(query):
    query_lower = query.lower()
    if "time" in query_lower:
        return f"Offline Fallback: The current local time is {datetime.datetime.now().strftime('%I:%M %p')}."
    elif "date" in query_lower:
        return f"Offline Fallback: Today is {datetime.datetime.now().strftime('%B %d, %Y')}."
    elif "hello" in query_lower or "hi" in query_lower:
        return "Offline Fallback: Hello! I am running in offline backup mode."
    elif "who are you" in query_lower or "your name" in query_lower:
        return f"Offline Fallback: I am your AI assistant, {Assistantname}."
    return "Offline Fallback: I am currently unable to contact the cloud APIs, and I don't have this information saved locally."


# Define a system message that provides context to the AI chatbot about its role and behavior.
System = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which also has real-time up-to-date information from the internet.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in Hindi, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""
# A list of system instructions for the chatbot.
SystemChatBot = [
{"role": "system", "content": System}
]


# Attempt to load the chat log from a JSON file.
try:
    with open(r"Data\ChatLog.json", "r") as f:
        messages = load(f) # Load existing messages from the chat log.
except FileNotFoundError: 
# If the file doesn't exist, create an empty JSON file to store chat logs.
        with open(r"Data\ChatLog.json", "w") as f:
            dump([], f)
# Function to get real-time date and time information.
def RealtimeInformation():
    current_date_time = datetime.datetime.now() # Get the current date and time.
    day = current_date_time.strftime("%A") # Day of the week.
    date = current_date_time.strftime("%d") # Day of the month.
    month = current_date_time.strftime("%B") # Full month name.
    year = current_date_time.strftime("%Y") # Year.
    hour = current_date_time.strftime("%H") # Hour in 24-hour format.
    minute = current_date_time.strftime("%M") # Minute.
    second = current_date_time.strftime("%S") # Second.

    # Format the information into a string.
    data = f"Please use this real-time information if needed, \n"
    data += f"Day: {day}\nDate: {date}\nMonth: {month}\nYear: {year}\n"
    data += f"Time: {hour} hours : {minute} minutes : {second} seconds.\n"
    return data
    I
# Function to modify the chatbot's response for better formatting.
def AnswerModifier(Answer):
    lines = Answer.split('\n') # Split the response into lines.
    non_empty_lines = [line for line in lines if line.strip()] # Remove empty lines.
    modified_answer = '\n'.join(non_empty_lines) # Join the cleaned lines back together.
    return modified_answer


# Main chatbot function to handle user queries.
def ChatBot(Query):
    """ This function sends the user's query to the chatbot and returns the AI's response."""
    
    try:
        # Load the existing chat log from the JSON file.
        with open(r"Data\ChatLog.json", "r") as f:
            messages = load(f)
        # Append the user's query to the messages list. I
        messages.append({"role": "user", "content": f"{Query}"})
        
        # Load long term facts dynamically and append to system instructions
        facts = get_all_facts()
        dynamic_system = System + facts
        current_system_messages = [{"role": "system", "content": dynamic_system}]
        
        Answer = None
        
        # 1. Try Groq (Primary Cloud Model)
        try:
            completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Specify the AI model to use.
            messages=current_system_messages + [{"role": "system", "content": RealtimeInformation()}] + messages, # Include system instructions, real-time info,
            max_tokens=1024, # Limit the maximum tokens in the response.
            temperature=0.7, # Adjust response randomness (higher means more random).
            top_p=1, # Use nucleus sampling to control diversity.
            stream=True, # Enable streaming response.
            stop=None # Allow the model to determine when to stop.
            )
            
            Answer = ""
            # Process the streamed response chunks.
            for chunk in completion:
                 if chunk.choices[0].delta.content: # Check if there's content in the current chunk.
                    Answer += chunk.choices[0].delta.content # Append the content to the answer.
            Answer = Answer.replace("</s>", "") # Clean up any unwanted tokens from the response.
        except Exception as groq_err:
            print(f"Primary Groq model failed: {groq_err}. Trying fallbacks...")
            
            # 2. Try Local Ollama (Local offline model)
            Answer = call_ollama_chat(messages, dynamic_system + "\n" + RealtimeInformation())
            
            if Answer is None:
                # 3. Try Cohere (Secondary Cloud Model)
                Answer = call_cohere_chat(messages, dynamic_system + "\n" + RealtimeInformation(), Query)
                
            if Answer is None:
                # 4. Try Offline Local Rules
                Answer = call_offline_fallback(Query)
        
        # Append the chatbot's response to the messages list.
        messages.append({"role": "assistant", "content": Answer})
        # Save the updated chat log to the JSON file.
        with open(r"Data\ChatLog.json", "w") as f:
            dump(messages, f, indent=4)
        # Trigger asynchronous fact extraction to save details permanently
        extract_facts_async(Query, Answer)

        # Return the formatted response.
        return AnswerModifier (Answer=Answer)

    except Exception as e:
        # Handle errors by printing the exception and resetting the chat log.
        print(f"Error in ChatBot: {e}")
        with open(r"Data\ChatLog.json", "w") as f:
            dump([], f, indent=4)
        return f"Sorry, I encountered an error: {e}"

#Main program entry point.
if __name__ == "__main__":
    while True:
        user_input = input("Enter Your Question: ") # Prompt the user for a question.
        print(ChatBot (user_input)) # Call the chatbot function and print its response.