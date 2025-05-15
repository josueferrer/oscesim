from openai import OpenAI
import os, backoff, time
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@backoff.on_exception(backoff.expo, Exception, max_tries=5, max_time=60)
def chat(messages, model="gpt-4o", temperature=0.2, max_tokens=600, retry_count=0):
    """
    Chat completion using OpenAI models with fallback mechanism
    - Input cost: $2.00 per 1M tokens
    - Output cost: $8.00 per 1M tokens
    - Context window: 1,047,576 tokens
    - Max output: 32,768 tokens
    - Knowledge cutoff: May 31, 2024
    """
    max_retries = 3
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            response_format={ "type": "text" }  # Ensuring text output
        )
        return response.choices[0].message.content
    except Exception as e:
        # If we've tried a few times with the specified model, try a fallback model
        if retry_count >= max_retries:
            # Fallback to a more reliable model if gpt-4.1 is having issues
            if model == "gpt-4.1":
                print(f"Error with gpt-4.1, falling back to gpt-4o: {str(e)}")
                return chat(messages, model="gpt-4o", temperature=temperature, max_tokens=max_tokens, retry_count=0)
            elif model == "gpt-4o":
                print(f"Error with gpt-4o, falling back to gpt-4o-mini: {str(e)}")
                return chat(messages, model="gpt-4o-mini", temperature=temperature, max_tokens=max_tokens, retry_count=0)
            else:
                # If we've exhausted all fallbacks, return an error message
                print(f"OpenAI API error with all models: {str(e)}")
                return "I apologize, but I encountered a service error. Please try again later."
        
        # Increment retry count and try again after a delay
        print(f"OpenAI API error (attempt {retry_count+1}): {str(e)}")
        time.sleep(2 * (retry_count + 1))  # Exponential backoff
        return chat(messages, model=model, temperature=temperature, max_tokens=max_tokens, retry_count=retry_count+1)

def patient_simulation(patient_case, user_message, chat_history=None, model="gpt-4o"):
    """
    Specialized function to simulate a patient's responses based on a generated case.
    
    Args:
        patient_case: The complete case data
        user_message: The current message from the user/medical student
        chat_history: Optional list of previous messages for context
        model: The LLM model to use
    
    Returns:
        A patient response that realistically simulates how a patient would answer
    """
    if chat_history is None:
        chat_history = []
    
    # Extract relevant patient details from case
    patient_info = patient_case.get("patientInfo", {})
    patient_name = patient_info.get("name", "Patient")
    patient_age = patient_info.get("age", "Unknown")
    patient_gender = patient_info.get("gender", "Unknown")
    occupation = patient_info.get("occupation", "Unknown")
    
    chief_complaint = patient_case.get("chiefComplaint", "Unknown complaint")
    history_details = patient_case.get("historyDetails", {})
    
    # Create a detailed patient simulation prompt
    system_message = {
        "role": "system",
        "content": f"""You are roleplaying as a patient named {patient_name}, {patient_age} years old, {patient_gender}, working as {occupation}. 
You are attending a medical consultation for: {chief_complaint}.

IMPORTANT GUIDELINES:
1. Respond AS THE PATIENT, not as an AI. Use first-person perspective.
2. You ONLY know what a real patient would know about their condition.
3. DO NOT volunteer information unless directly asked.
4. DO NOT use medical terminology the patient wouldn't know.
5. Express appropriate emotions (worry, pain, confusion) based on your condition.
6. If asked about a symptom you don't have, simply deny it naturally.
7. Your answers should be concise and realistic - keep responses under 2-3 sentences unless pressed for details.
8. Maintain consistent details throughout the interaction.

YOUR MEDICAL DETAILS:
- Chief complaint: {chief_complaint}
- History: {history_details}
- Past medical history: {patient_case.get('pastMedicalHistory', [])}
- Medications: {patient_case.get('medications', [])}
- Social history: {patient_case.get('socialHistory', {})}

Remember to act like a real patient with this condition would - with appropriate knowledge gaps, concerns, and communication style."""
    }
    
    # Construct the complete conversation
    messages = [system_message] + chat_history + [{"role": "user", "content": user_message}]
    
    # Use a higher temperature for more realistic, variable patient responses
    return chat(messages, model=model, temperature=0.7, max_tokens=150) 