import json, difflib
from openai_utils import chat
from checklist import HISTORY_ITEMS, EXAM_ITEMS, MANAGEMENT_ITEMS

def checklist_score(lang, transcript):
    items = HISTORY_ITEMS + EXAM_ITEMS + MANAGEMENT_ITEMS
    sys = {"role":"system",
        "content":(
            f"You are an OSCE examiner scoring in {lang}. "
            "For EACH checklist item respond 0/1 (missed/done). "
            "Return JSON list of binary ints."
        )}
    usr = {"role":"user","content":f"Transcript:\n{transcript}\n\nChecklist:\n"+"\n".join(items)}
    raw = chat([sys, usr], model="gpt-4.1", temperature=0.1)
    try:
        done = json.loads(raw)
    except:
        done = [0]*len(items)
    total = sum(done) / len(items) * 100
    missed = [items[i] for i,v in enumerate(done) if v==0]
    return total, missed

def diagnosis_score(student_dx, answer_key):
    correct = answer_key["main_diagnosis"]
    sim = difflib.SequenceMatcher(None, student_dx.lower(), correct.lower()).ratio()
    return 100 if sim > 0.8 else 0, correct

def evaluate(lang, transcript, student_dx, answer_key):
    cl_score, missed = checklist_score(lang, transcript)
    dx_score, correct = diagnosis_score(student_dx, answer_key)
    total = round(0.8*cl_score + 0.2*dx_score,1)
    return {
        "checklist_pct": round(cl_score,1),
        "diagnosis_pct": dx_score,
        "overall_pct": total,
        "missed_items": missed,
        "correct_dx": correct
    } 