import json, random, re
from openai_utils import chat
from prompt_templates import CASE_GENERATION_PROMPT, CUSTOM_CASE_PROMPT

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

def generate_station(lang="en", custom_case=None, specialty=None):
    """
    Generate a complete OSCE station with all necessary parameters.
    
    Args:
        lang: Language for the case
        custom_case: Optional dict with custom case parameters provided by the user
        specialty: Optional medical specialty to filter chief complaints
    
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
    
    # Construct the system prompt using our template
    sys_msg = {"role": "system", 
              "content": CASE_GENERATION_PROMPT.format(
                  lang=lang,
                  age=patient_age,
                  gender=patient_gender,
                  chief=chief
              )}
    
    usr = {"role": "user", "content": f"Generate a detailed OSCE station for chief complaint: {chief} {case_type}"}
    
    # Using a safe model with temperature 0.4 for creative but medically accurate case generation
    max_attempts = 3
    required_fields = ["patientInfo", "chiefComplaint", "historyDetails", "labResults", 
                       "imagingResults", "reviewOfSystems", "answer_key"]
    
    for attempt in range(max_attempts):
        try:
            # First, get the raw text response
            raw_response = chat([sys_msg, usr], model="gpt-4o", temperature=0.4)
            
            # Try to fix any JSON formatting issues
            fixed_json = fix_json_string(raw_response)
            
            # Parse the fixed JSON
            try:
                case_data = json.loads(fixed_json)
                
                # Check if we have all required fields
                missing_fields = [field for field in required_fields if field not in case_data]
                if missing_fields:
                    # If we have missing fields and this isn't the last attempt, try again
                    if attempt < max_attempts - 1:
                        usr = {"role": "user", "content": f"The case is missing these fields: {', '.join(missing_fields)}. Please regenerate a complete OSCE case with all required fields including: {', '.join(required_fields)}"}
                        continue
                    # On last attempt, fill in the missing fields
                    else:
                        for field in missing_fields:
                            if field == "patientInfo":
                                case_data["patientInfo"] = create_patient_info(patient_age, patient_gender)
                            elif field == "chiefComplaint":
                                case_data["chiefComplaint"] = chief
                            elif field == "historyDetails":
                                case_data["historyDetails"] = create_default_history()
                            elif field == "labResults":
                                case_data["labResults"] = {}
                            elif field == "imagingResults":
                                case_data["imagingResults"] = {}
                            elif field == "reviewOfSystems":
                                case_data["reviewOfSystems"] = {}
                            elif field == "answer_key":
                                case_data["answer_key"] = {
                                    "main_diagnosis": f"Unspecified {chief.lower()}",
                                    "differentials": ["Alternative diagnosis 1", "Alternative diagnosis 2"],
                                    "management": ["Symptomatic treatment", "Follow-up in 2 weeks"]
                                }
                
                # We have a valid case with all required fields, break out of the loop
                break
                
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
                        # If all parsing fails and this is the last attempt, create a minimal case
                        if attempt == max_attempts - 1:
                            case_data = create_fallback_case(chief, patient_age, patient_gender, lang)
                        else:
                            continue
                else:
                    # If no JSON-like structure found and this is the last attempt, create a minimal case
                    if attempt == max_attempts - 1:
                        case_data = create_fallback_case(chief, patient_age, patient_gender, lang)
                    else:
                        continue
        except Exception as e:
            print(f"Error generating station: {str(e)}")
            # If this is the last attempt, create a fallback case
            if attempt == max_attempts - 1:
                case_data = create_fallback_case(chief, patient_age, patient_gender, lang)
            else:
                continue
    
    # Add timestamp to track when this case was generated
    case_data["generated_timestamp"] = int(random.random() * 10000000)
    
    # Ensure case_data has all required fields
    ensure_required_fields(case_data, chief, patient_age, patient_gender)
    
    return case_data

def create_patient_info(age, gender):
    """Create realistic patient information"""
    # Create proper names based on gender
    if gender.lower() == "male":
        name = random.choice([
            "James Wilson", "Michael Smith", "Robert Johnson", 
            "Daniel Brown", "David Lee", "John Davis", 
            "Thomas Garcia", "Richard Martinez", "Joseph Robinson", 
            "Charles Wright"
        ])
        occupation = random.choice([
            "Office worker", "Engineer", "Teacher", "Salesperson", 
            "Construction worker", "Retired", "IT specialist", 
            "Driver", "Business owner", "Student"
        ])
    else:
        name = random.choice([
            "Mary Williams", "Patricia Jones", "Jennifer Taylor", 
            "Linda Anderson", "Elizabeth Thomas", "Barbara Jackson", 
            "Susan White", "Jessica Harris", "Sarah Martin", 
            "Karen Thompson"
        ])
        occupation = random.choice([
            "Office worker", "Teacher", "Nurse", "Sales representative", 
            "Homemaker", "Retired", "Student", "Manager", 
            "Healthcare worker", "Business owner"
        ])
    
    return {
        "name": name,
        "age": age,
        "gender": gender,
        "occupation": occupation
    }

def create_default_history():
    """Create a default history object when missing"""
    return {
        "onset": "3 days ago",
        "duration": "Continuous",
        "character": "Moderate",
        "aggravating": "Physical activity",
        "relieving": "Rest"
    }

def create_fallback_case(chief, age, gender, lang):
    """Create a simple fallback case when JSON parsing fails"""
    return {
        "patientInfo": create_patient_info(age, gender),
        "chiefComplaint": chief,
        "historyDetails": create_default_history(),
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
        case_data["patientInfo"] = create_patient_info(age, gender)
    elif "name" not in case_data["patientInfo"] or case_data["patientInfo"]["name"].startswith("Patient_"):
        # Ensure patient has a real name, not a generic one
        if case_data["patientInfo"].get("gender", "").lower() == "male":
            case_data["patientInfo"]["name"] = random.choice([
                "James Wilson", "Michael Smith", "Robert Johnson", 
                "Daniel Brown", "David Lee", "John Davis"
            ])
        else:
            case_data["patientInfo"]["name"] = random.choice([
                "Mary Williams", "Patricia Jones", "Jennifer Taylor", 
                "Linda Anderson", "Elizabeth Thomas", "Barbara Jackson"
            ])
    
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
    
    # Ensure historyDetails
    if "historyDetails" not in case_data:
        case_data["historyDetails"] = create_default_history()
        
    # Add any other missing fields with empty defaults
    for field in ["pastMedicalHistory", "familyHistory", "medications", 
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
    
    sys_msg = {"role": "system", "content": CUSTOM_CASE_PROMPT.format(lang=lang)}
    
    usr = {"role": "user", "content": f"Create an OSCE case based on this description: {case_description}"}
    
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