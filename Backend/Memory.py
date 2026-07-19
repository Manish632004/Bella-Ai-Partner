import os
import sqlite3
import json
import re
import threading

DB_PATH = r"Data/jarvis_memory.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        fact_key TEXT PRIMARY KEY,
        fact_value TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def remember_fact(key, value):
    init_db()
    # Normalize key (convert to lowercase and replace spaces with underscores)
    normalized_key = key.strip().lower().replace(" ", "_")
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO memory (fact_key, fact_value) VALUES (?, ?)",
        (normalized_key, value.strip())
    )
    conn.commit()
    conn.close()
    return f"I have committed this to my long-term memory: {normalized_key} is {value.strip()}."

def recall_fact(key):
    init_db()
    normalized_key = key.strip().lower().replace(" ", "_")
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute("SELECT fact_value FROM memory WHERE fact_key = ?", (normalized_key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return f"Regarding '{normalized_key}', I remember: {row[0]}."
    return f"I could not find any long-term memory about '{normalized_key}'."

def get_all_facts():
    init_db()
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT fact_key, fact_value FROM memory")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    
    if not rows:
        return ""
    
    facts_str = "\n".join([f"- {r[0]}: {r[1]}" for r in rows])
    return f"\n*** Long-Term User Facts/Memory ***\nYou must remember these persistent facts about the user:\n{facts_str}\n"

def auto_extract_facts(user_query, assistant_response):
    """Analyzes conversation segment to extract and save user facts/preferences in the background."""
    prompt = f"""
    Analyze the following conversation segment between a User and an AI Assistant.
    Extract any key personal facts, preferences, settings, or details about the User (such as their name, location, address, hobbies, job, studies, likes/dislikes) that should be remembered permanently.
    Do not extract temporary states, generic conversational text, or questions.
    Format your output as a single flat JSON object with lowercase string keys (using underscores for spaces) and string values.
    If no personal facts or details are present, output only an empty JSON object: {{}}
    
    Conversation:
    User: {user_query}
    Assistant: {assistant_response}
    
    Output JSON:
    """
    
    facts_json = None
    
    # Try Groq API first
    try:
        from Backend.Chatbot import client
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=256,
            response_format={"type": "json_object"}
        )
        facts_json = completion.choices[0].message.content
    except Exception as e:
        print(f"Auto-extract Groq failed: {e}. Trying Cohere fallback...")
        # Fallback to Cohere
        try:
            from Backend.Chatbot import CohereAPIKey
            import cohere
            co = cohere.Client(api_key=CohereAPIKey)
            response = co.chat(
                model="command-r-plus-08-2024",
                message=prompt,
                temperature=0.1
            )
            text = response.text
            match = re.search(r"\{.*?\}", text, re.DOTALL)
            if match:
                facts_json = match.group(0)
        except Exception as cohere_err:
            print(f"Auto-extract Cohere failed: {cohere_err}")
            
    if facts_json:
        try:
            facts = json.loads(facts_json)
            for k, v in facts.items():
                remember_fact(k, str(v))
                print(f"[MEMORY AUTO-REMEMBERED]: {k} -> {v}")
        except Exception as parse_err:
            print(f"Error parsing auto-extracted facts: {parse_err}")

def extract_facts_async(user_query, assistant_response):
    t = threading.Thread(target=auto_extract_facts, args=(user_query, assistant_response), daemon=True)
    t.start()
