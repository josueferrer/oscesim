import json, difflib
from openai_utils import chat
from checklist import CHECKLIST, WEIGHTS, MAX_SCORE
from prompt_templates import EVALUATION_PROMPT

def checklist_score(lang, transcript, case=None):
    """
    Calculate scores for checklist items based on transcript and case details.
    Now includes separate scoring for history, examination, management, lab, and interaction.
    """
    # Create a detailed system prompt
    sys = {"role":"system",
        "content":(
            f"You are a medical OSCE examiner scoring in {lang}. "
            "Carefully evaluate this student's performance against standard OSCE marking criteria. "
            "For EACH checklist item, respond with a score: "
            "0 (Not Done), 3 (Partially Done), or 5 (Well Done). "
            "Return a JSON object with these sections: "
            "'history', 'exam', 'lab', 'management', 'interaction' (each with arrays of scores), "
            "'overall_comments' (string with brief feedback)"
        )}
    
    # Create a detailed user prompt with case context if available
    prompt_content = f"Transcript:\n{transcript}\n\nChecklist Items:\n"
    
    # Add each section's items
    for section, items in CHECKLIST.items():
        prompt_content += f"\n{section.upper()}:\n"
        prompt_content += "\n".join(f"- {item}" for item in items)
    
    # Add case details if available
    if case:
        prompt_content += f"\n\nCase Information (for context):\n"
        prompt_content += f"Chief Complaint: {case.get('chiefComplaint', 'Unknown')}\n"
        prompt_content += f"Diagnosis: {case.get('answer_key', {}).get('main_diagnosis', 'Unknown')}"
    
    usr = {"role":"user","content": prompt_content}
    
    # Using GPT-4o for scoring - low temperature for consistency and accuracy
    try:
        raw = chat([sys, usr], model="gpt-4o", temperature=0.1, max_tokens=1000)
        scores = json.loads(raw)
        
        # Calculate section percentages and collect raw scores
        if isinstance(scores, dict):
            raw_scores = {}
            total_raw = 0
            total_possible = 0
            
            for section, items in CHECKLIST.items():
                section_scores = scores.get(section, [])
                
                # Ensure we have scores for each item (use 0 if missing)
                if len(section_scores) < len(items):
                    section_scores = section_scores + [0] * (len(items) - len(section_scores))
                elif len(section_scores) > len(items):
                    section_scores = section_scores[:len(items)]
                
                # Store raw scores
                raw_scores[section] = section_scores
                
                # Calculate totals
                section_total = sum(section_scores)
                section_possible = len(items) * 5
                total_raw += section_total
                total_possible += section_possible
            
            # Calculate overall percentage
            overall_pct = (total_raw / total_possible * 100) if total_possible > 0 else 0
            
            # Calculate section percentages
            section_pcts = {}
            for section, items in CHECKLIST.items():
                section_scores = raw_scores.get(section, [])
                section_possible = len(items) * 5
                section_pct = (sum(section_scores) / section_possible * 100) if section_possible > 0 else 0
                section_pcts[f"{section}_pct"] = round(section_pct, 1)
            
            # Identify missed items (scored 0)
            missed_items = []
            for section, items in CHECKLIST.items():
                section_scores = raw_scores.get(section, [])
                for i, score in enumerate(section_scores):
                    if i < len(items) and score == 0:
                        missed_items.append(items[i])
            
            # Combine results
            result = {
                "total_pct": round(overall_pct, 1),
                "raw_scores": raw_scores,
                "missed_items": missed_items,
                "comments": scores.get('overall_comments', '')
            }
            
            # Add section percentages
            result.update(section_pcts)
            
            return result
            
        # Fallback to simple scoring if complex format fails
        else:
            return {
                "total_pct": 0,
                "history_pct": 0,
                "exam_pct": 0,
                "lab_pct": 0,
                "management_pct": 0,
                "interaction_pct": 0,
                "missed_items": [item for section in CHECKLIST.values() for item in section],
                "comments": "Evaluation error occurred - could not parse scores"
            }
    except Exception as e:
        print(f"Error in evaluation: {str(e)}")
        # Fallback for any parsing error
        return {
            "total_pct": 0,
            "history_pct": 0,
            "exam_pct": 0,
            "lab_pct": 0,
            "management_pct": 0,
            "interaction_pct": 0,
            "missed_items": [item for section in CHECKLIST.values() for item in section],
            "comments": f"Evaluation error occurred: {str(e)}"
        }

def diagnosis_score(student_dx, answer_key):
    """
    Calculate score for the diagnosis accuracy.
    Returns a percentage score (0, 50, 100) based on how well the student's
    diagnosis matches the correct diagnosis or differentials.
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
        return 75, correct
    else:
        # Check if it matches any differential diagnosis
        for diff_dx in differentials:
            diff_sim = difflib.SequenceMatcher(None, student_dx.lower(), diff_dx.lower()).ratio()
            if diff_sim > 0.7:
                return 50, correct  # Partial credit for identifying a differential
        
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
    
    # Calculate weighted total score (80% checklist, 20% diagnosis)
    # This weighting aligns with the official marking sheet where diagnosis is important
    # but doesn't override the whole performance
    total = round(0.8 * checklist_results["total_pct"] + 0.2 * dx_score, 1)
    
    # Combine all results
    result = {
        "overall_pct": total,
        "checklist_pct": checklist_results["total_pct"],
        "history_pct": checklist_results.get("history_pct", 0),
        "exam_pct": checklist_results.get("exam_pct", 0),
        "lab_pct": checklist_results.get("lab_pct", 0),
        "management_pct": checklist_results.get("management_pct", 0),
        "interaction_pct": checklist_results.get("interaction_pct", 0),
        "diagnosis_pct": dx_score,
        "raw_scores": checklist_results.get("raw_scores", {}),
        "missed_items": checklist_results["missed_items"],
        "correct_dx": correct_dx,
        "comments": checklist_results.get("comments", "")
    }
    
    return result

def render_mark_sheet(raw_scores, student_dx, correct_dx, dx_score, total_score, comments):
    """
    Render a formatted mark sheet for the examiner view.
    """
    md = ["### Examiner's Mark Sheet", "| Item | Score |", "|---|---|"]
    idx = 1
    
    for section, items in CHECKLIST.items():
        section_title = section.capitalize()
        if section == "lab":
            section_title = "Lab and Radiology"
        elif section == "interaction":
            section_title = "Doctor/Patient Interaction (5%)"
            
        md.append(f"**{section_title}:**")
        
        section_scores = raw_scores.get(section, [0] * len(items))
        for i, item in enumerate(items):
            score = section_scores[i] if i < len(section_scores) else 0
            score_text = "ND=0" if score == 0 else "PD=3" if score == 3 else "WD=5"
            md.append(f"| {idx}. {item} | {score} ({score_text}) |")
            idx += 1
    
    # Add diagnosis and total
    md.append("\n**Diagnosis Assessment:**")
    md.append(f"Student diagnosis: {student_dx}")
    md.append(f"Correct diagnosis: {correct_dx}")
    md.append(f"Diagnosis score: {dx_score}%")
    
    # Global rating
    rating = "Clear Pass" if total_score >= 70 else "Borderline" if total_score >= 60 else "Clear Fail"
    md.append(f"\n**Total Score:** {total_score:.1f}% ({int(MAX_SCORE * total_score / 100)}/{MAX_SCORE})")
    md.append(f"\n**Global Rating:** {rating}")
    
    # Comments
    md.append("\n**Examiner's Comments:**")
    md.append(comments or "No specific comments provided.")
    
    return "\n".join(md) 