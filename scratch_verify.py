import sys
import os
import time
from datetime import datetime

# Add the workspace directory to sys.path to ensure absolute imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import src.config as config
from src.ai_feedback import AiFeedbackCoach

def test_ai_feedback():
    print("=== Starting AI Study Coach verification tests ===", flush=True)
    
    # 1. Test CSV Generation
    csv_path = config.CALENDAR_EVENTS_CSV_PATH
    if os.path.exists(csv_path):
        print(f"Removing existing calendar CSV at {csv_path} to test generation...", flush=True)
        os.remove(csv_path)
        
    coach = AiFeedbackCoach()
    print("Instantiated AiFeedbackCoach.", flush=True)
    
    # Reading events should trigger file creation
    events = coach._read_upcoming_events()
    print(f"Read {len(events)} upcoming events.", flush=True)
    
    if os.path.exists(csv_path):
        print("SUCCESS: calendar_events.csv was successfully created!", flush=True)
        with open(csv_path, "r", encoding="utf-8") as f:
            print("CSV Contents:")
            print(f.read())
    else:
        print("FAIL: calendar_events.csv was not created.")
        sys.exit(1)

    # 2. Test Trigger Checking
    print("\n--- Testing Trigger Logic ---", flush=True)
    
    # Base context (normal state)
    base_context = {
        "focus_score": 90,
        "consecutive_distracted_seconds": 0,
        "today_time_seconds": 120,
        "session_time_seconds": 60,
        "target_study_time_hours": 4.0,
        "today_time_text": "00:02:00",
        "session_time_text": "00:01:00",
        "posture_score": 85,
        "posture_status": "Good",
        "focus_status": "Focused",
        "focused_time_text": "00:01:50",
        "max_focused_time_text": "00:01:00",
        "away_time_text": "00:00:00",
        "no_face_time_text": "00:00:00",
        "study_state": "Focused"
    }
    
    # Case 1: Normal state (no triggers)
    triggered = coach._check_triggers(base_context, events)
    print(f"Normal context trigger check: {triggered} (Expected: False)")
    if triggered:
        print("FAIL: normal context should not fire a trigger.")
        sys.exit(1)
        
    # Case 2: Focus score below 45
    low_focus_context = base_context.copy()
    low_focus_context["focus_score"] = 40
    triggered = coach._check_triggers(low_focus_context, events)
    print(f"Low focus context trigger check: {triggered} (Expected: True)")
    if not triggered:
        print("FAIL: focus score < 45 should trigger.")
        sys.exit(1)
        
    # Case 3: Away/No face for >= 20 seconds
    distracted_context = base_context.copy()
    distracted_context["consecutive_distracted_seconds"] = 25
    triggered = coach._check_triggers(distracted_context, events)
    print(f"Away/No-face >= 20s trigger check: {triggered} (Expected: True)")
    if not triggered:
        print("FAIL: consecutive distraction >= 20s should trigger.")
        sys.exit(1)

    # Case 4: Today's study time behind target (session >= 5 mins)
    behind_context = base_context.copy()
    behind_context["session_time_seconds"] = 310
    behind_context["today_time_seconds"] = 310  # 310s is far behind 4 hours
    triggered = coach._check_triggers(behind_context, events)
    print(f"Behind target study time trigger check: {triggered} (Expected: True)")
    if not triggered:
        print("FAIL: being behind study target after 5 mins should trigger.")
        sys.exit(1)

    # 3. Test Prompt Construction
    print("\n--- Testing Prompt Construction ---", flush=True)
    prompt = coach._build_prompt(base_context, events)
    print("Generated Prompt:")
    print("==================================================")
    print(prompt)
    print("==================================================")
    
    # 4. Check environmental API Key
    api_key_status = "FOUND" if coach.api_key else "NOT FOUND (.env or environment variable missing)"
    print(f"\nGEMINI_API_KEY status: {api_key_status}", flush=True)
    
    print("\n=== All local logic tests passed! ===")

if __name__ == "__main__":
    test_ai_feedback()
