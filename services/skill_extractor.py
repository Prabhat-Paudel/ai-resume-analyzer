
import re


SKILLS = [
    "Python",
    "Java",
    "JavaScript",
    "C",
    "C++",
    "C#",
    "PHP",
    "Flask",
    "Django",
    "HTML",
    "CSS",
    "React",
    "Node.js",
    "SQL",
    "MySQL",
    "PostgreSQL",
    "MongoDB",
    "Git",
    "GitHub",
    "Docker",
    "AWS",
    "Azure",
    "Machine Learning",
    "Data Analysis",
    "Pandas",
    "NumPy",
    "Excel",
    "Communication",
    "Problem Solving",
    "Teamwork",
]


def extract_skills(text):
    """
    Find known skills in resume text.
    """

    found_skills = []

    text_lower = text.lower()

    for skill in SKILLS:
        pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"

        if re.search(pattern, text_lower):
            found_skills.append(skill)

    return found_skills
