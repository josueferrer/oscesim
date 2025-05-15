import json, random
from openai_utils import chat

def generate_station(lang="en"):
    chief = random.choice(["Chest pain", "Abdominal pain", "Early pregnancy bleeding"])
    sys_msg = {"role":"system",
       "content":(
        f"You are an OSCE station generator. Language={lang}. "
        "Return STRICT JSON with keys:"
        " chiefComplaint, historyPrompts(list), physicalFindings(list),"
        " answer_key {main_diagnosis, differentials(list)}."
       )}
    usr = {"role":"user","content":f"Generate an OSCE station for chief complaint: {chief}"}
    return json.loads(chat([sys_msg, usr], model="gpt-4o")) 