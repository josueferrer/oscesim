import json, random
from openai_utils import chat

def generate_station(lang="en", custom_case=None):
    """
    Generate a complete OSCE station with all necessary parameters.
    
    Args:
        lang: Language for the case
        custom_case: Optional dict with custom case parameters provided by the user
    
    Returns:
        A complete case dictionary with all needed information
    """
    if custom_case:
        # Use custom case parameters provided by the user
        chief = custom_case.get("chief_complaint", "")
        patient_age = custom_case.get("age", random.randint(18, 85))
        patient_gender = custom_case.get("gender", random.choice(["male", "female"]))
        case_type = custom_case.get("case_type", "")
    else:
        # Generate a random case
        chief_options = [
            "Chest pain", "Abdominal pain", "Headache", 
            "Shortness of breath", "Joint pain", "Early pregnancy bleeding",
            "Dizziness", "Fever", "Back pain", "Cough", "Rash"
        ]
        chief = random.choice(chief_options)
        patient_age = random.randint(18, 85)
        patient_gender = random.choice(["male", "female"])
        case_type = ""
    
    # Construct a detailed system prompt for comprehensive case generation
    sys_msg = {"role":"system",
       "content":(
        f"You are an expert medical OSCE case generator. Create a detailed, realistic OSCE station in {lang}. "
        f"The case involves a {patient_age}-year-old {patient_gender} presenting with {chief}. "
        "Generate a medically accurate and detailed case including:"
        "\n1. Patient demographics (name, age, occupation)"
        "\n2. Detailed presenting complaint with onset, duration, severity"
        "\n3. Relevant past medical history"
        "\n4. Family history"
        "\n5. Medication history"
        "\n6. Social history (smoking, alcohol, living situation)"
        "\n7. Review of systems findings"
        "\n8. Physical examination findings"
        "\n9. Laboratory results (if relevant)"
        "\n10. Imaging results (if relevant)"
        "\n11. The hidden diagnosis the student should discover"
        "\n12. Key history questions the student should ask"
        "\n13. Key physical exam maneuvers the student should perform"
        "\n14. Appropriate management steps"
        "\nProduce a STRICT JSON response with the following keys:"
        "\n- patientInfo (object with name, age, gender, occupation)"
        "\n- chiefComplaint (string)"
        "\n- historyDetails (object with onset, duration, character, aggravating factors, relieving factors)"
        "\n- pastMedicalHistory (array of strings)"
        "\n- familyHistory (array of strings)"
        "\n- medications (array of strings)"
        "\n- socialHistory (object with smoking, alcohol, living)"
        "\n- reviewOfSystems (object with relevant systems)"
        "\n- physicalFindings (array of strings)"
        "\n- labResults (object with test names and values)"
        "\n- imagingResults (object with types and findings)"
        "\n- keyHistoryQuestions (array of strings with questions student should ask)"
        "\n- keyExamManeuvers (array of strings with exams student should perform)"
        "\n- answer_key (object with main_diagnosis, differentials array, management array)"
       )}
    
    usr = {"role":"user","content":f"Generate a detailed OSCE station for chief complaint: {chief} {case_type}"}
    
    # Using GPT-4.1 with temperature 0.4 for creative but medically accurate case generation
    case_data = json.loads(chat([sys_msg, usr], model="gpt-4.1", temperature=0.4))
    
    # Add timestamps to track when this case was generated
    case_data["generated_timestamp"] = int(random.random() * 10000000)
    
    return case_data

def custom_case_generator(lang="en", case_description=""):
    """Generate a custom case based on user description"""
    
    sys_msg = {"role":"system",
        "content":(
            f"You are a medical expert OSCE case creator. Language={lang}. "
            "First, extract the key clinical details from the user's description. "
            "Then create a complete OSCE case based on these details. "
            "Return a strict JSON with all medical details needed for an OSCE station."
        )}
    
    usr = {"role":"user","content":f"Create an OSCE case based on this description: {case_description}"}
    
    # Extract basic case parameters
    params_extraction = chat([sys_msg, usr], model="gpt-4.1", temperature=0.2)
    
    try:
        # Try to parse the extraction result
        extracted_data = json.loads(params_extraction)
        return generate_station(lang, extracted_data)
    except:
        # If parsing fails, create a case with just the description as chief complaint
        custom_data = {"chief_complaint": case_description}
        return generate_station(lang, custom_data) 