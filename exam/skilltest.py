from exam.question import Question
from typing import List, Any
import json


class SkillTest:
    questions: List[Question] = []

    def __init__(self):
        with open('exam/questions.json', 'r') as q_json:
            for q in json.load(q_json):
                new_q = Question(q.get("id"), q.get("question"), q.get("answers"), q.get("correct_index"))
                self.questions.append(new_q)

    def as_list(self):
        res = []
        for q in self.questions:
            res.append(q.as_dict())
        return res

    def as_list_with_answers(self, user_answers: List[Any]):
        assert(len(self.questions) == len(user_answers))
        res = []
        for i in range(len(self.questions)):
            q = self.questions[i].as_dict()
            q.update({"user_answer": user_answers[i]})
            res.append(q)
        return res
