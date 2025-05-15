"""
OSCE Examination Checklist

This module contains the comprehensive 35-item rubric used for evaluating OSCE performance.
Each item is scored as:
- Well Done (WD): 5 points
- Partially Done (PD): 3 points
- Not Done (ND): 0 points
"""

CHECKLIST = {
  "history": [
    "Greets the patient / introduces self and establishes good rapport",
    "Clarifies details of the chief complaint",
    "Asks about associated symptoms related to the presenting system",
    "Rules out emergency case red flags",
    "Rules out B-symptom red flags",
    "Performs review of systems",
    "Takes obstetric and gynecological history (for female patients)",
    "Asks about past medical history: includes admissions, chronic diseases, similar episodes",
    "Asks about past surgical history",
    "Asks about drug and allergy history",
    "Asks about family history",
    "Takes social history: diet, exercise, alcohol, drugs, smoking, occupation, marital status, etc.",
    "Takes neonatal history (for pediatric patients): mode of delivery, gestational age, diseases, infections, medications, pregnancy history, birth weight, postnatal admissions",
    "Asks about developmental milestones (for pediatric patients)",
    "Elicits ICEE (Ideas, Concerns, Expectations, and Effects on life)",
    "Screens using PHQ2",
    "Screens for vaccination and preventive health relevant to age and sex"
  ],
  "exam": [
    "Takes permission, washes hands, maintains privacy",
    "Measures vital signs",
    "Assesses general appearance",
    "Examines the main system involved in the chief complaint",
    "Examines related systems as relevant to the main system",
    "Elicits specific signs to confirm the suspected diagnosis",
    "Performs focused examinations if specific instruments are provided"
  ],
  "lab": [
    "Orders or explains lab investigations as required",
    "Recognizes and interprets radiological findings appropriately"
  ],
  "management": [
    "Clarifies diagnosis and explains management options",
    "Reassures the patient with empathy and honesty",
    "Provides non-pharmacological advice",
    "Prescribes pharmacological treatment",
    "Refers to appropriate services as needed (specialists, physiotherapy, nutrition, smoking cessation, social worker, etc.)",
    "Orders further investigations as needed",
    "Advises on follow-up/observation",
    "Discusses disease prevention and health promotion (e.g. vaccines, screenings)"
  ],
  "interaction": [
    "Demonstrates effective communication (verbal and non-verbal), active listening, open-ended questions, and empathy"
  ]
}

# Each item is 5 points for WD, 3 for PD, 0 for ND
WEIGHTS = {i: 5 for i in range(1, 36)}  # 1→5, 2→5, …, 35→5

# Calculate the maximum possible score
MAX_SCORE = 160  # As specified in the official marking sheet 