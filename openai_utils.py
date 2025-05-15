import os, json, backoff
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@backoff.on_exception(backoff.expo, Exception, max_tries=5, max_time=60)
def chat(messages, model="gpt-4o", temperature=0.2, max_tokens=600, return_json=False):
    """
    Send a request to the OpenAI API and return the response.
    Uses exponential backoff for rate limit and other errors.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        result = response.choices[0].message.content
        
        if return_json:
            try:
                # Try to parse as JSON
                return json.loads(result)
            except json.JSONDecodeError:
                # If not valid JSON, return the raw response
                return result
        return result
    except Exception as e:
        print(f"Error in chat function: {str(e)}")
        if return_json:
            return {}
        return f"Error: {str(e)}"

def patient_simulation(patient_case, user_message, chat_history, model="gpt-4o"):
    """
    Simulate a patient response based on the case details and chat history.
    """
    # Extract relevant patient details
    patient_info = patient_case.get("patientInfo", {})
    name = patient_info.get("name", "Patient")
    age = patient_info.get("age", "Unknown")
    gender = patient_info.get("gender", "Unknown")
    chief = patient_case.get("chiefComplaint", "Unknown complaint")
    
    # Construct the system prompt
    system_prompt = {
        "role": "system", 
        "content": (
            f"You are simulating a patient named {name}, {age} years old, {gender}, "
            f"who has come to the doctor with: {chief}. "
            "Respond as the patient would based on the medical case details provided. "
            "Be natural, realistic, and consistent with the case details. "
            "The user is a medical student practicing for their OSCE exam. "
            "Do not volunteer all information at once - make the student ask appropriate questions. "
            "Correct information is important but the student must elicit it through proper questioning."
        )
    }
    
    # Add case details to help guide the AI
    context = {
        "role": "system",
        "content": (
            "Case details (not to be directly revealed unless asked):\n" +
            f"- History: {patient_case.get('historyDetails', {})}\n" +
            f"- Past medical history: {patient_case.get('pastMedicalHistory', [])}\n" +
            f"- Medications: {patient_case.get('medications', [])}\n" +
            f"- Social history: {patient_case.get('socialHistory', {})}\n" +
            f"- Review of systems: {patient_case.get('reviewOfSystems', {})}\n" +
            f"- Physical findings: {patient_case.get('physicalFindings', [])}"
        )
    }
    
    # Format the chat history
    messages = [system_prompt, context]
    
    # Add chat history
    for msg in chat_history:
        if msg["role"] in ["user", "assistant"]:
            messages.append(msg)
    
    # Add the current user message
    messages.append({"role": "user", "content": user_message})
    
    # Get response using the main chat function
    return chat(messages, model=model, temperature=0.4) 