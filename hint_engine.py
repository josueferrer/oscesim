from openai_utils import chat
from checklist import CHECKLIST
from prompt_templates import HINT_GENERATION_PROMPT

def generate_hint(lang, transcript):
    """
    Generate a helpful hint for the student based on their transcript and the OSCE checklist.
    Returns a relevant hint for an important aspect they may have missed in their examination.
    """
    system = {"role": "system", "content": HINT_GENERATION_PROMPT.format(lang=lang)}
    user = {"role": "user", "content": transcript}
    
    # Using GPT-4o for medical education hints - moderate temperature for balanced suggestions
    return chat([system, user], model="gpt-4o", temperature=0.3) 