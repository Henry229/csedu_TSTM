import json
import base64
import random
import time
from locust import HttpUser, task, between

STRESS_TEST_TOKEN = "7QXgZGbIdVC1fSJB3pnXE28ZZjSfhktp"


class QuickstartUser(HttpUser):
    # 각 request 간에 1초에서 2.5 초 간격을 둡니다.
    wait_time = between(1, 2.5)

    # Assessment 관련된 정보
    assessment_guid = "3a7b5e92-208b-4cf8-8a99-c0cb14416a29"
    testset_id = 8
    # {item_id: response} 형식입니다.
    responses = {
        6: {"base": {"identifier": "C"}}
    }

    # /api/session 에서 받아옵니다.
    session = ""
    # /api/start 에서 받아옵니다.
    questions = []

    def select_question(self):
        """
        /api/start 에서 받아온 question 중에서 random 하게 하나를 선택합니다.
        """
        selected_index = random.randint(0, len(self.questions)-1)
        return self.questions[selected_index]

    @task
    def rendered01(self):
        question = self.select_question()
        item_id = question.get('item_id')
        response = self.client.get(f'/api/rendered/{item_id}', params={"session": self.session},
                                   cookies=self.client.cookies.get_dict())
        # print(response.text)

    @task
    def response01(self):
        question = self.select_question()
        item_id = question.get('item_id')
        marking_id = question.get('marking_id')
        question_no = question.get('question_no')
        answer = self.responses.get(item_id, "")
        response = self.client.post(f"/api/responses/{item_id}",
                                    json={"session": self.session, "question_no": question_no,
                                          "marking_id": marking_id,
                                          "response": {"RESPONSE": answer}})
        # print(response.json())
        print(response)

    def on_start(self):
        token = {"sid": "csetest5", "aid": self.assessment_guid, "sto": 120,
                 "type": "stresstest", "stresstest_token": STRESS_TEST_TOKEN}
        token_base64 = base64.b64encode(json.dumps(token).encode()).decode()
        self.client.get("/inward?token=" + token_base64)
        # print(self.client.cookies.get_dict())
        response = self.client.post("/api/session",
                                    json={"assessment_guid": self.assessment_guid, "testset_id": self.testset_id,
                                          "student_ip": "123.243.86.1", "start_time": int(time.time()),
                                          "tnc_agree_checked": True}, cookies=self.client.cookies.get_dict())
        self.session = response.json().get('data').get('session')
        response = self.client.post("/api/start", json={"session": self.session}, cookies=self.client.cookies.get_dict())
        print(response.json())
        self.questions = response.json().get('data').get('new_questions')

