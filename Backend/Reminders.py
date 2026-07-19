import os
import sqlite3
import datetime
import re
import time
import threading
from Backend.TextToSpeech import TextToSpeech
from Frontend.GUI import ShowTextToScreen, SetAssistantStatus

DB_PATH = r"Data/jarvis_memory.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        time TEXT NOT NULL,
        is_triggered INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        fact_key TEXT PRIMARY KEY,
        fact_value TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def parse_time(time_str):
    time_str = time_str.lower().strip()
    
    # Match relative times like "in 5 minutes", "1 hour", etc.
    match = re.match(r"(?:in\s+)?(\d+)\s*(minute|minutes|min|mins|hour|hours|hr|hrs|day|days|d)", time_str)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        now = datetime.datetime.now()
        if "minute" in unit or "min" in unit:
            target_time = now + datetime.timedelta(minutes=amount)
        elif "hour" in unit or "hr" in unit:
            target_time = now + datetime.timedelta(hours=amount)
        elif "day" in unit or "d" in unit:
            target_time = now + datetime.timedelta(days=amount)
        return target_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Try parsing absolute times
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p"):
        try:
            parsed = datetime.datetime.strptime(time_str, fmt)
            if fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p"):
                now = datetime.datetime.now()
                parsed = now.replace(hour=parsed.hour, minute=parsed.minute, second=parsed.second if "%S" in fmt else 0, microsecond=0)
                if parsed < now:
                    parsed += datetime.timedelta(days=1)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
            
    # Default fallback: 5 minutes from now
    print(f"Warning: Could not parse time '{time_str}', defaulting to 5 minutes from now.")
    return (datetime.datetime.now() + datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

def add_reminder(text, time_str):
    init_db()
    parsed_time = parse_time(time_str)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reminders (text, time) VALUES (?, ?)",
        (text, parsed_time)
    )
    conn.commit()
    conn.close()
    return f"Reminder successfully set for {parsed_time}: '{text}'"

def list_reminders():
    init_db()
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, text, time FROM reminders WHERE is_triggered = 0 ORDER BY time ASC"
    )
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "You have no active reminders."
        
    res = "Active Reminders:\n"
    for r in rows:
        res += f"ID: {r[0]} | Time: {r[2]} | Task: {r[1]}\n"
    return res.strip()

def delete_reminder(reminder_id):
    init_db()
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute("SELECT text FROM reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return f"No active reminder found with ID {reminder_id}."
    cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()
    return f"Successfully deleted reminder ID {reminder_id}: '{row[0]}'."

def check_reminders_loop():
    while True:
        try:
            init_db()
            conn = sqlite3.connect(DB_PATH, timeout=20)
            cursor = conn.cursor()
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute(
                "SELECT id, text, time FROM reminders WHERE is_triggered = 0 AND time <= ?",
                (now_str,)
            )
            due_reminders = cursor.fetchall()
            
            for r in due_reminders:
                rid, rtext, rtime = r
                cursor.execute(
                    "UPDATE reminders SET is_triggered = 1 WHERE id = ?",
                    (rid,)
                )
                conn.commit()
                
                announcement = f"Reminder: {rtext}"
                print(f"\n[REMINDER DUE]: {announcement}")
                ShowTextToScreen(f"Bella : [Reminder] {rtext}")
                SetAssistantStatus("Answering...")
                TextToSpeech(announcement)
                
            conn.close()
        except Exception as e:
            print(f"Error in reminders background check: {e}")
            
        time.sleep(30)

def start_reminder_scheduler():
    t = threading.Thread(target=check_reminders_loop, daemon=True)
    t.start()
    print("Reminder scheduler background thread started.")
