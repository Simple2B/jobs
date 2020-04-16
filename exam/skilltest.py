from exam.question import Question
from typing import List, Any
import json


class SkillTest:
    questions: List[Question]

    def __init__(self):
        self.questions = []
        with open('exam/questions.json', 'r') as q_json:
            for q in json.load(q_json):
                new_q = Question(q.get("id"), q.get("question"), q.get("answers"), q.get("correct_index"))
                self.questions.append(new_q)

    def as_list(self):
        return [q.as_dict() for q in self.questions]

    def as_list_with_answers(self, user_answers: List[Any]):
        """ представим вопрос в виде dict-а, и допишем в него ответ пользователя.
        set из таких обновлённых вопросов будем писать в БД в виде строки
        (что-то вроде json.dumps(SkillTest().as_list_with_answers(SkilltestForm.user_answers))"""
        assert(len(self.questions) == len(user_answers))
        res = []
        for i in range(len(self.questions)):
            q = self.questions[i].as_dict()
            q.update({"user_answer": user_answers[i]})
            res.append(q)
        return res
