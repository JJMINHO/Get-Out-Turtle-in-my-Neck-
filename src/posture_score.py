# Posture scoring module.
# This file will calculate posture-related angles and convert them into a score.

def classify_score(score):
    if score >= 80:
        return "Good"
    elif score >= 60:
        return "Warning"
    else:
        return "Bad"
