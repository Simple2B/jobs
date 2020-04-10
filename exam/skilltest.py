from typing import List
from exam.question import Question
import json


class SkillTest:
    questions: List[Question] = []

    def __init__(self):
        with open('exam/questions.json', 'r') as q_json:
            for q in json.load(q_json):
                new_q = Question(q.get("id"), q.get("question"), q.get("answers"), q.get("correct_index"))
                self.questions.append(new_q)
