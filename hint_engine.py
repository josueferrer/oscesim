from openai_utils import chat
from checklist import HISTORY_ITEMS, EXAM_ITEMS

def generate_hint(lang, transcript):
    system = {"role":"system",
              "content":f"You are an OSCE tutor. Read transcript and point OUT ONE important history or exam question the student has not yet asked. Language={lang}. If nothing to add answer 'No hint'."}
    user = {"role":"user","content":transcript}
    # Using GPT-4.1 for medical education hints - moderate temperature for balanced suggestions
    return chat([system, user], model="gpt-4.1", temperature=0.3) 