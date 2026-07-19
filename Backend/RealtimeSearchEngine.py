from googlesearch import search
from groq import Groq # Importing the Groq library to use its API.
from json import load, dump # Importing functions to read and write JSON files.
import datetime # Importing the datetime module for real-time date and time information.
from dotenv import dotenv_values # Importing dotenv_values to read environment variables from a .env file.
from Backend.Memory import get_all_facts, extract_facts_async
from Backend.Chatbot import call_cohere_chat, call_ollama_chat, call_offline_fallback



#Load environment variables from the env file.

env_vars = dotenv_values(".env")
#Retrieve environment variables for the chatbot configuration.
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey = env_vars.get("GroqAPIKey")

#Initialize the Groq client with the provided API key.
client = Groq(api_key=GroqAPIKey)

# Define the system instructions for the chatbot

System = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which has real-time up-to-date information from the internet.
*** Provide Answers In a Professional Way, make sure to add full stops, commas, question marks, and use proper grammar.***
*** Just answer the question from the provided data in a professional way. ***"""

# Try to load the chat log from a JSON file, or create an empty one if it doesn't ex

try:
    with open(r"Data\ChatLog.json", "r") as f:
        messages = load(f)
except:
    with open(r"Data\ChatLog.json", "w") as f:
        dump([], f)

# Function to perform a Google search and format the results.

def GoogleSearch(query):
    results = list(search(query, advanced=True, num_results=5))
    Answer = f"The search results for '{query}' are:\n[start]\n"

    for i in results:
        Answer += f"Title: {i.title}\nDescription: {i.description}\n\n"

    Answer += "[end]"
    return Answer

#Function to clean up the answer by removing empty lines.
def AnswerModifier (Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

#Predefined chatbot conversation system message and an initial user message.
SystemChatBot = [

{"role": "system", "content": System},

{"role": "user", "content": "Hi"},

{"role": "assistant", "content": "Hello, how can I help you?"}

]
#Function to get real-time information like the current date and time.
def Information():
    data = ""
    current_date_time = datetime.datetime.now()
    day = current_date_time
    date = current_date_time.strftime("%d")
    month= current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    hour = current_date_time.strftime("%H")
    minute = current_date_time.strftime("%M")
    second = current_date_time.strftime("%S")
    data += f"Use This Real-time Information if needed:\n"
    data += f"Day: {day}\n"
    data += f"Date: {date}\n"
    data += f"Month: {month}\n"
    data += f"Year: {year}\n"
    data += f"Time: {hour} hours, {minute} minutes, {second} seconds.\n"
    return data

#Function to handle real-time search and response generation.
def RealtimeSearchEngine (prompt):
    global messages
    #Load the chat log from the JSON file.
    with open(r"Data\ChatLog.json", "r") as f:
        messages = load(f)
    messages.append({"role": "user", "content": f"{prompt}"})

    # Reconstruct dynamic system prompt with long term facts
    facts = get_all_facts()
    dynamic_system = System + facts
    google_results = GoogleSearch(prompt)
    local_system_chatbot = [
        {"role": "system", "content": dynamic_system},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello, how can I help you?"},
        {"role": "system", "content": google_results}
    ]

    try:
        # 1. Try Groq
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=local_system_chatbot + [{"role": "system", "content": Information()}] + messages,
            temperature=0.7,
            max_tokens=2048,
            stream=True,
            stop=None
        )
        Answer = ""
        # Concatenate response chunks from the streaming output.
        for chunk in completion:
            if chunk.choices[0].delta.content:
                Answer += chunk.choices[0].delta.content
        Answer = Answer.strip().replace("</s>", "")
    except Exception as groq_err:
        print(f"RealtimeSearchEngine Groq model failed: {groq_err}. Trying fallbacks...")
        
        # Combine instructions and search results for fallback preamble
        combined_system = dynamic_system + "\n" + Information() + "\n" + google_results
        
        # 2. Try Local Ollama
        Answer = call_ollama_chat(messages, combined_system)
        
        if Answer is None:
            # 3. Try Cohere
            Answer = call_cohere_chat(messages, combined_system, prompt)
            
        if Answer is None:
            # 4. Try Offline Local Rules
            Answer = call_offline_fallback(prompt)

    messages.append({"role": "assistant", "content": Answer})

    # Trigger asynchronous fact extraction to save details permanently
    extract_facts_async(prompt, Answer)

    #Save the updated chat log back to the JSON file.
    with open(r"Data\ChatLog.json", "w") as f:
        dump(messages, f, indent=4)

    return AnswerModifier (Answer=Answer)
# Main entry point of the program for interactive querying.
if __name__ == "__main__":
        while True:
            prompt = input("Enter your query:")
            print(RealtimeSearchEngine(prompt))
