from typing import List


class Question:
    id
    question: str
    answers: List[str]
    correct_index: int

    def __init__(self, id, question: str, answers: List[str], correct_index: int):
        self.id = id
        self.question = question
        self.answers = answers
        self.correct_index = correct_index
