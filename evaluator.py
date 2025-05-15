import json, difflib
from openai_utils import chat
from checklist import HISTORY_ITEMS, EXAM_ITEMS, MANAGEMENT_ITEMS

def checklist_score(lang, transcript, case=None):
    """
    Calculate scores for checklist items based on transcript and case details.
    Now includes separate scoring for history, examination, and management.
    """
    # Combine all checklist items
    items = HISTORY_ITEMS + EXAM_ITEMS + MANAGEMENT_ITEMS
    
    # Create a detailed system prompt
    sys = {"role":"system",
        "content":(
            f"You are a medical OSCE examiner scoring in {lang}. "
            "Carefully evaluate this student's performance against standard OSCE marking criteria. "
            "For EACH checklist item, respond with a score: "
            "0 (Not Done), 3 (Partially Done), or 5 (Well Done). "
            "Return a JSON object with these sections: "
            "'history' (scores for history items), "
            "'exam' (scores for exam items), "
            "'management' (scores for management items), "
            "'overall_comments' (string with brief feedback)"
        )}
    
    # Create a detailed user prompt with case context if available
    prompt_content = f"Transcript:\n{transcript}\n\nChecklist Items:\n"
    
    # Add history items
    prompt_content += "\nHISTORY TAKING:\n" + "\n".join(f"- {item}" for item in HISTORY_ITEMS)
    
    # Add exam items
    prompt_content += "\n\nEXAMINATION:\n" + "\n".join(f"- {item}" for item in EXAM_ITEMS)
    
    # Add management items
    prompt_content += "\n\nMANAGEMENT:\n" + "\n".join(f"- {item}" for item in MANAGEMENT_ITEMS)
    
    # Add case details if available
    if case:
        prompt_content += f"\n\nCase Information (for context):\n"
        prompt_content += f"Chief Complaint: {case.get('chiefComplaint', 'Unknown')}\n"
        prompt_content += f"Diagnosis: {case.get('answer_key', {}).get('main_diagnosis', 'Unknown')}"
    
    usr = {"role":"user","content": prompt_content}
    
    # Using GPT-4.1 for scoring - low temperature for consistency and accuracy
    try:
        raw = chat([sys, usr], model="gpt-4.1", temperature=0.1, max_tokens=1000)
        scores = json.loads(raw)
        
        # Calculate section percentages
        if isinstance(scores, dict):
            history_scores = scores.get('history', [])
            exam_scores = scores.get('exam', [])
            management_scores = scores.get('management', [])
            
            # Calculate percentages for each section
            history_pct = sum(history_scores) / (len(HISTORY_ITEMS) * 5) * 100 if HISTORY_ITEMS else 0
            exam_pct = sum(exam_scores) / (len(EXAM_ITEMS) * 5) * 100 if EXAM_ITEMS else 0
            management_pct = sum(management_scores) / (len(MANAGEMENT_ITEMS) * 5) * 100 if MANAGEMENT_ITEMS else 0
            
            # Combine all scores to calculate total checklist percentage
            all_scores = history_scores + exam_scores + management_scores
            total_pct = sum(all_scores) / (len(items) * 5) * 100
            
            # Identify missed items (scored 0)
            missed_history = [HISTORY_ITEMS[i] for i, score in enumerate(history_scores) if i < len(HISTORY_ITEMS) and score == 0]
            missed_exam = [EXAM_ITEMS[i] for i, score in enumerate(exam_scores) if i < len(EXAM_ITEMS) and score == 0]
            missed_management = [MANAGEMENT_ITEMS[i] for i, score in enumerate(management_scores) if i < len(MANAGEMENT_ITEMS) and score == 0] 
            
            missed_items = missed_history + missed_exam + missed_management
            
            return {
                "total_pct": round(total_pct, 1),
                "history_pct": round(history_pct, 1),
                "exam_pct": round(exam_pct, 1),
                "management_pct": round(management_pct, 1),
                "missed_items": missed_items,
                "comments": scores.get('overall_comments', '')
            }
        
        # Fallback to simple list scoring if complex format fails
        elif isinstance(scores, list):
            done = scores
            total = sum(done) / len(items) * 100
            missed = [items[i] for i,v in enumerate(done) if v==0 and i < len(items)]
            return {
                "total_pct": round(total, 1),
                "missed_items": missed,
                "comments": "No detailed scoring available"
            }
    except Exception as e:
        print(f"Error in evaluation: {str(e)}")
        # Fallback for any parsing error
        return {
            "total_pct": 0,
            "history_pct": 0,
            "exam_pct": 0,
            "management_pct": 0,
            "missed_items": items,
            "comments": "Evaluation error occurred"
        }

def diagnosis_score(student_dx, answer_key):
    """
    Calculate score for the diagnosis accuracy.
    """
    correct = answer_key["main_diagnosis"]
    differentials = answer_key.get("differentials", [])
    
    # Check for main diagnosis match
    sim = difflib.SequenceMatcher(None, student_dx.lower(), correct.lower()).ratio()
    
    if sim > 0.8:
        # Excellent match with main diagnosis
        return 100, correct
    elif sim > 0.6:
        # Good approximation of main diagnosis
        return 80, correct
    else:
        # Check if it matches any differential diagnosis
        for diff_dx in differentials:
            diff_sim = difflib.SequenceMatcher(None, student_dx.lower(), diff_dx.lower()).ratio()
            if diff_sim > 0.7:
                return 60, correct  # Partial credit for identifying a differential
        
        # No matches
        return 0, correct

def evaluate(lang, transcript, student_dx, answer_key, case=None):
    """
    Evaluate the student's performance based on transcript and diagnosis.
    Returns a comprehensive evaluation object.
    """
    # Get checklist scores
    checklist_results = checklist_score(lang, transcript, case)
    
    # Get diagnosis score
    dx_score, correct_dx = diagnosis_score(student_dx, answer_key)
    
    # Calculate weighted total score (70% checklist, 30% diagnosis)
    total = round(0.7 * checklist_results["total_pct"] + 0.3 * dx_score, 1)
    
    # Combine all results
    result = {
        "overall_pct": total,
        "checklist_pct": checklist_results["total_pct"],
        "history_pct": checklist_results.get("history_pct", 0),
        "exam_pct": checklist_results.get("exam_pct", 0),
        "management_pct": checklist_results.get("management_pct", 0),
        "diagnosis_pct": dx_score,
        "missed_items": checklist_results["missed_items"],
        "correct_dx": correct_dx,
        "comments": checklist_results.get("comments", "")
    }
    
    return result 