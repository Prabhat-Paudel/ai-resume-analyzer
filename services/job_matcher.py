
def match_job(resume_skills, job_description):
    """
    Compare resume skills with skills required in a job description.
    """

    from services.skill_extractor import extract_skills

    required_skills = extract_skills(job_description)

    matched_skills = [
        skill for skill in required_skills
        if skill.lower() in [s.lower() for s in resume_skills]
    ]

    missing_skills = [
        skill for skill in required_skills
        if skill.lower() not in [s.lower() for s in resume_skills]
    ]

    if required_skills:
        match_score = round(
            len(matched_skills) / len(required_skills) * 100
        )
    else:
        match_score = 0

    suggestions = []

    if missing_skills:
        suggestions.append(
            "Consider gaining experience in: "
            + ", ".join(missing_skills)
        )

    if not suggestions:
        suggestions.append(
            "Your resume includes all detected skills required by this job."
        )

    return {
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "suggestions": suggestions,
    }
