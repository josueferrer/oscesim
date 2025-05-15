import json, random, re
from openai_utils import chat

def fix_json_string(json_str):
    """
    Attempt to fix common JSON formatting issues in the model's output.
    """
    # Remove any markdown formatting that might be around the JSON
    json_str = re.sub(r'^```json\s*', '', json_str)
    json_str = re.sub(r'\s*```$', '', json_str)
    
    # Sometimes model adds commentary before or after the JSON
    if json_str.find('{') > 0:
        json_str = json_str[json_str.find('{'):]
    if json_str.rfind('}') < len(json_str) - 1:
        json_str = json_str[:json_str.rfind('}')+1]
        
    return json_str

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
        "\n\nIMPORTANT: ONLY return valid JSON without any additional text, markdown formatting, or explanation."
       )}
    
    usr = {"role":"user","content":f"Generate a detailed OSCE station for chief complaint: {chief} {case_type}"}
    
    # Using a safe model with temperature 0.4 for creative but medically accurate case generation
    try:
        # First, get the raw text response
        raw_response = chat([sys_msg, usr], model="gpt-4o", temperature=0.4)
        
        # Try to fix any JSON formatting issues
        fixed_json = fix_json_string(raw_response)
        
        # Parse the fixed JSON
        try:
            case_data = json.loads(fixed_json)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {str(e)}")
            # If still failing, try a more aggressive cleanup
            # Extract anything that looks like JSON
            json_match = re.search(r'\{.*\}', fixed_json, re.DOTALL)
            if json_match:
                try:
                    case_data = json.loads(json_match.group(0))
                except Exception as e2:
                    print(f"Secondary parse error: {str(e2)}")
                    # If all parsing fails, create a minimal case
                    case_data = create_fallback_case(chief, patient_age, patient_gender, lang)
            else:
                case_data = create_fallback_case(chief, patient_age, patient_gender, lang)
    except Exception as e:
        print(f"Error generating station: {str(e)}")
        case_data = create_fallback_case(chief, patient_age, patient_gender, lang)
    
    # Add timestamps to track when this case was generated
    case_data["generated_timestamp"] = int(random.random() * 10000000)
    
    # Ensure case_data has all required fields
    ensure_required_fields(case_data, chief, patient_age, patient_gender)
    
    return case_data

def create_fallback_case(chief, age, gender, lang):
    """Create a simple fallback case when JSON parsing fails"""
    return {
        "patientInfo": {
            "name": f"Patient_{random.randint(1000, 9999)}",
            "age": age,
            "gender": gender,
            "occupation": "Office worker"
        },
        "chiefComplaint": chief,
        "historyDetails": {
            "onset": "3 days ago",
            "duration": "Continuous",
            "character": "Moderate",
            "aggravating": "Physical activity",
            "relieving": "Rest"
        },
        "pastMedicalHistory": ["None significant"],
        "familyHistory": ["None significant"],
        "medications": ["None"],
        "socialHistory": {"smoking": "No", "alcohol": "Occasional", "living": "With family"},
        "reviewOfSystems": {},
        "physicalFindings": ["Normal vital signs", "Mild discomfort"],
        "labResults": {},
        "imagingResults": {},
        "keyHistoryQuestions": ["Ask about onset", "Ask about severity", "Ask about associated symptoms"],
        "keyExamManeuvers": ["Check vital signs", "Examine affected area"],
        "answer_key": {
            "main_diagnosis": "Unspecified " + chief.lower(),
            "differentials": ["Alternative diagnosis 1", "Alternative diagnosis 2"],
            "management": ["Symptomatic treatment", "Follow-up in 2 weeks"]
        }
    }

def ensure_required_fields(case_data, chief, age, gender):
    """Ensure all required fields exist in the case data"""
    # Check patientInfo
    if "patientInfo" not in case_data:
        case_data["patientInfo"] = {
            "name": f"Patient_{random.randint(1000, 9999)}",
            "age": age,
            "gender": gender,
            "occupation": "Office worker"
        }
    
    # Ensure chief complaint
    if "chiefComplaint" not in case_data:
        case_data["chiefComplaint"] = chief
    
    # Ensure answer_key
    if "answer_key" not in case_data:
        case_data["answer_key"] = {
            "main_diagnosis": "Unspecified " + chief.lower(),
            "differentials": ["Alternative diagnosis 1", "Alternative diagnosis 2"],
            "management": ["Symptomatic treatment", "Follow-up in 2 weeks"]
        }
        
    # Add any other missing fields with empty defaults
    for field in ["historyDetails", "pastMedicalHistory", "familyHistory", "medications", 
                "socialHistory", "reviewOfSystems", "physicalFindings", "labResults", 
                "imagingResults", "keyHistoryQuestions", "keyExamManeuvers"]:
        if field not in case_data:
            if field in ["pastMedicalHistory", "familyHistory", "medications", 
                        "physicalFindings", "keyHistoryQuestions", "keyExamManeuvers"]:
                case_data[field] = []
            else:
                case_data[field] = {}

def custom_case_generator(lang="en", case_description=""):
    """Generate a custom case based on user description"""
    
    sys_msg = {"role":"system",
        "content":(
            f"You are a medical expert OSCE case creator. Language={lang}. "
            "First, extract the key clinical details from the user's description. "
            "Then create a complete OSCE case based on these details. "
            "Return a strict JSON with all medical details needed for an OSCE station."
            "\n\nIMPORTANT: ONLY return valid JSON without any additional text."
        )}
    
    usr = {"role":"user","content":f"Create an OSCE case based on this description: {case_description}"}
    
    try:
        # Extract basic case parameters
        params_extraction = chat([sys_msg, usr], model="gpt-4o", temperature=0.2)
        
        # Try to parse as JSON
        try:
            extracted_data = json.loads(fix_json_string(params_extraction))
            return generate_station(lang, extracted_data)
        except json.JSONDecodeError as e:
            print(f"Custom case JSON parse error: {str(e)}")
            # If parsing fails, create a case with just the description as chief complaint
            custom_data = {"chief_complaint": case_description}
            return generate_station(lang, custom_data)
    except Exception as e:
        print(f"Error in custom case generation: {str(e)}")
        # Fallback to basic station generation
        return generate_station(lang, {"chief_complaint": case_description}) 