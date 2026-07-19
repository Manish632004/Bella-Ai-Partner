import ssl 
ssl._create_default_https_context = ssl._create_unverified_context
from Frontend.GUI import (
GraphicalUserInterface,
SetAssistantStatus,
ShowTextToScreen,
TempDirectoryPath,
SetMicrophoneStatus,
AnswerModifier,
QueryModifier,
GetMicrophoneStatus,
GetAssistantStatus )
from Backend.Model import FirstLayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from Backend.Automation import Automation
from Backend.SpeechToText import SpeechRecognition
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
from Backend.FileTools import find_file, read_file, list_directory, debug_code
from Backend.Reminders import start_reminder_scheduler, add_reminder, list_reminders, delete_reminder
from Backend.Memory import remember_fact, recall_fact
from dotenv import dotenv_values
from asyncio import run
from time import sleep
import subprocess
import threading
import json
import os

env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
DefaultMessage = f'''{Username}: Hello {Assistantname}, How are you?
{Assistantname}: Welcome {Username}. I am doing well. How may i help you?'''
subprocesses = []
Functions = ["open", "close", "play", "system", "content", "google search", "youtube search"]

def ShowDefaultChatIfNoChats():

        File = open(r'Data\ChatLog.json', "r", encoding='utf-8') 
        if len(File.read())<5:
            with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
                file.write("")
            with open(TempDirectoryPath('Responses.data'), 'w', encoding='utf-8') as file:
                file.write(DefaultMessage)

def ReadChatLogJson():
        with open(r'Data\ChatLog.json', 'r', encoding='utf-8') as file:
            chatlog_data = json.load(file)
        return chatlog_data

def ChatLogIntegration():
        json_data = ReadChatLogJson()
        formatted_chatlog = ""
        for entry in json_data:
           if entry["role"] == "user":
                formatted_chatlog += f"User: {entry['content']}\n"
           elif entry["role"] == "assistant":
                formatted_chatlog += f"Assistant: {entry['content']}\n"
        formatted_chatlog = formatted_chatlog.replace("User", Username + " ")
        formatted_chatlog = formatted_chatlog.replace("Assistant", Assistantname + " ")

        with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
            file.write(AnswerModifier(formatted_chatlog))
def ShowChatsOnGUI():
        
        File =open(TempDirectoryPath('Database.data'), "r", encoding='utf-8') 
        Data = File.read()
        if len(str(Data))>0:
            lines =Data.split('\n')
            result = '\n'.join(lines)
            File.close()
            File = open(TempDirectoryPath('Responses.data'), "w", encoding='utf8')
            File.write(result)
            File.close()
def InitialExecution():
        SetMicrophoneStatus("False")
        ShowTextToScreen("")
        ShowDefaultChatIfNoChats()
        ChatLogIntegration()
        ShowChatsOnGUI()
        start_reminder_scheduler()
InitialExecution()
def MainExecution():
        TaskExecution = False
        ImageExecution  =False
        ImageGenerationQuery = ""
        SetAssistantStatus("Listening... ")
        Query = SpeechRecognition()
        ShowTextToScreen(f"{Username}: {Query}")
        SetAssistantStatus("Thinking...")
        Decision =FirstLayerDMM(Query)
        print("")
        print(f"Decision: {Decision}")
        print("")
        G = any([i for i in Decision if i.startswith("general")])
        R = any([i for i in Decision if i.startswith("realtime")])
        Mearged_query = " and ".join(
        ["".join(i.split()[1:]) for i in Decision if i.startswith("general") or i.startswith("realtime")]
        )
        for queries in Decision:
            if "generate" in queries:
                ImageGenerationQuery = str(queries)
                ImageExecution = True
        for queries in Decision:
            if TaskExecution == False:
                if any(queries.startswith(func) for func in Functions): run(Automation (list(Decision)))
                TaskExecution = True
        if ImageExecution == True:
            with open(r"Frontend\Files\ImageGeneration.data", "w") as file:
                file.write(f" {ImageGenerationQuery}, True")
            try:
                p1 = subprocess.Popen (['python', r'Backend\ImageGeneration.py'],
                                    stdout=subprocess. PIPE, stderr=subprocess.PIPE,
                                    stdin=subprocess. PIPE, shell=False)
                subprocesses.append(p1)

            except Exception as e:
                print(f"Error starting ImageGeneration.py: {e}")

        if G and R or R:

                SetAssistantStatus("Searching...")
                Answer = RealtimeSearchEngine (QueryModifier (Mearged_query))
                ShowTextToScreen(f" {Assistantname} : {Answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(Answer)
                return True
        else:

                for Queries in Decision:
                    if "general" in Queries:
                        SetAssistantStatus("Thinking ... ")
                        QueryFinal = Queries.replace( "general","")
                        Answer = ChatBot(QueryModifier (QueryFinal))
                        ShowTextToScreen(f" {Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True
                    elif "realtime" in Queries:
                        SetAssistantStatus("Searching...")
                        QueryFinal = Queries.replace("realtime ","")
                        Answer = RealtimeSearchEngine (QueryModifier (QueryFinal))
                        ShowTextToScreen(f" {Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True
                    elif "set a reminder" in Queries:
                        SetAssistantStatus("Setting reminder...")
                        QueryFinal = Queries.replace("set a reminder", "").strip()
                        if " | " in QueryFinal:
                            time_part, message_part = QueryFinal.split(" | ", 1)
                            time_part = time_part.strip()
                            message_part = message_part.strip()
                        else:
                            time_part = "5 minutes"
                            message_part = QueryFinal
                        result = add_reminder(message_part, time_part)
                        prompt = f"The user requested to set a reminder. The system execution result is: '{result}'. Formulate a natural voice confirmation to the user."
                        Answer = ChatBot(prompt)
                        ShowTextToScreen(f" {Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True
                    elif "list my reminders" in Queries:
                        SetAssistantStatus("Listing reminders...")
                        result = list_reminders()
                        prompt = f"The user asked to list their reminders. The system data is:\n{result}\nFormulate a natural response presenting this list to the user."
                        Answer = ChatBot(prompt)
                        ShowTextToScreen(f" {Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True
                    elif "cancel a reminder" in Queries:
                        import re
                        SetAssistantStatus("Canceling reminder...")
                        QueryFinal = Queries.replace("cancel a reminder", "").strip()
                        id_match = re.search(r"\d+", QueryFinal)
                        if id_match:
                            rid = int(id_match.group(0))
                            result = delete_reminder(rid)
                        else:
                            result = "Could not find a valid reminder ID in the request."
                        prompt = f"The user requested to cancel a reminder. The cancellation outcome is: '{result}'. Formulate a natural response confirming the deletion or failure."
                        Answer = ChatBot(prompt)
                        ShowTextToScreen(f" {Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True
                    elif "remember fact" in Queries:
                        SetAssistantStatus("Remembering fact...")
                        QueryFinal = Queries.replace("remember fact", "").strip()
                        if " | " in QueryFinal:
                            key_part, value_part = QueryFinal.split(" | ", 1)
                            key_part = key_part.strip()
                            value_part = value_part.strip()
                        else:
                            key_part = "unknown"
                            value_part = QueryFinal
                        result = remember_fact(key_part, value_part)
                        prompt = f"The user asked to remember a fact. The memory system response is: '{result}'. Formulate a natural voice confirmation to the user."
                        Answer = ChatBot(prompt)
                        ShowTextToScreen(f" {Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True
                    elif "recall fact" in Queries:
                        SetAssistantStatus("Recalling fact...")
                        QueryFinal = Queries.replace("recall fact", "").strip()
                        result = recall_fact(QueryFinal)
                        prompt = f"The user asked to recall a fact for key '{QueryFinal}'. The memory lookup result is: '{result}'. Formulate a natural voice response presenting the fact."
                        Answer = ChatBot(prompt)
                        ShowTextToScreen(f" {Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True
                    elif "find file" in Queries:
                        SetAssistantStatus("Searching files...")
                        QueryFinal = Queries.replace("find file", "").strip()
                        if " | " in QueryFinal:
                            name, search_path = QueryFinal.split(" | ", 1)
                            name = name.strip()
                            search_path = search_path.strip()
                        else:
                            name = QueryFinal
                            search_path = "."
                        result = find_file(name, search_path)
                        prompt = f"The user asked to find files matching '{name}' in path '{search_path}'. Here is the list of matches found on the system:\n{result}\nFormulate a natural response informing the user about the results."
                        Answer = ChatBot(prompt)
                        ShowTextToScreen(f" {Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True
                    elif "read file" in Queries:
                        SetAssistantStatus("Reading file...")
                        QueryFinal = Queries.replace("read file", "").strip()
                        result = read_file(QueryFinal)
                        prompt = f"The user asked to read the file '{QueryFinal}'. Here are the contents of that file:\n```\n{result}\n```\nFormulate a natural response presenting the file content or summarizing it as appropriate."
                        Answer = ChatBot(prompt)
                        ShowTextToScreen(f" {Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True
                    elif "list files" in Queries:
                        SetAssistantStatus("Listing folder...")
                        QueryFinal = Queries.replace("list files", "").strip()
                        result = list_directory(QueryFinal if QueryFinal else ".")
                        prompt = f"The user asked to list the contents of the folder '{QueryFinal}'. Here is the directory listing:\n{result}\nFormulate a natural response summarizing the contents."
                        Answer = ChatBot(prompt)
                        ShowTextToScreen(f" {Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True
                    elif "debug code" in Queries:
                        SetAssistantStatus("Debugging code...")
                        QueryFinal = Queries.replace("debug code", "").strip()
                        if " | " in QueryFinal:
                            file_path, error_message = QueryFinal.split(" | ", 1)
                            file_path = file_path.strip()
                            error_message = error_message.strip()
                            if error_message.lower() == "none":
                                error_message = None
                        else:
                            file_path = QueryFinal
                            error_message = None
                        result = debug_code(file_path, error_message)
                        prompt = f"The user asked to debug the file '{file_path}' with error: '{error_message}'. Here is the debugging output from the analysis engine:\n{result}\nFormulate a natural response presenting the debugging analysis and the suggested fix."
                        Answer = ChatBot(prompt)
                        ShowTextToScreen(f" {Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True
                    elif "exit" in Queries:
                        QueryFinal = "Okay, Bye!"
                        Answer = ChatBot (QueryModifier (QueryFinal))
                        ShowTextToScreen(f"{Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        SetAssistantStatus("Answering...")
                        os._exit(1)
def FirstThread():
    while True:
        CurrentStatus = GetMicrophoneStatus()
        if CurrentStatus == "True":
            try:
                MainExecution()
            except Exception as e:
                print(f"Error in MainExecution: {e}")
                SetAssistantStatus("Error, listening again...")
                sleep(1)
        else:
            AIStatus = GetAssistantStatus()

            if "Available..." in AIStatus:
                sleep(0.1)
            else:
                SetAssistantStatus("Available...")
                
def SecondThread():

    GraphicalUserInterface()

if __name__== "__main__":

        thread2 = threading.Thread(target=FirstThread, daemon=True)
        thread2.start()
        SecondThread()