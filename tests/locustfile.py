import json
import base64
import random
import string
import time
from locust import HttpUser, task, between

"""
@ Terminal 에서 실행 방법
tests 폴더로 이동후
locust -f locustfile.py --headless -H http://localhost:5000 -u 2 -r 2 -t 30s
-H : 시험하고자하는 호스트 URL
-u : 사용자수
-r : 초당 몇명의 사용자를 활성화할지 결정.
마지막 -t 옵션은 30초 동안 실행을 한다는 의미임. 없으면 ctrl+c 를 누를때까지 계속함.

@ Web browser 로 보기
tests 폴더로 이동후
locust -f locustfile.py
웹브라우저를 띠우고 필요한 값을 입력합니다.
"""

STRESS_TEST_TOKEN = "7QXgZGbIdVC1fSJB3pnXE28ZZjSfhktp"


def get_random_string(length=16):
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join((random.choice(letters_and_digits) for i in range(length)))


class QuickstartUser(HttpUser):
    # 각 request 간에 1초에서 2.5 초 간격을 둡니다.
    wait_time = between(0.5, 3.5)

    # Assessment 관련된 정보
    assessment_guid = "4716ca6d-7be2-4ad7-aff8-b0c417aa95e6"
    testset_id = 633
    # Local 시험용
    # assessment_guid = "3a7b5e92-208b-4cf8-8a99-c0cb14416a29"
    # testset_id = 8
    # {item_id: response} 형식입니다.
    # 맞는 item_id가 없으면 default 를 불러갑니다.
    responses = {
        21190: {"base": {"identifier": "C"}},
    }
    responses_default = {"base": {"identifier": "A"}}

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
        response = self.client.get(f'/api/rendered/{item_id}', name='/api/rendered/item_id',
                                   params={"session": self.session, "r_key": get_random_string()},
                                   cookies=self.client.cookies.get_dict())
        # print(response.text)

    @task
    def response01(self):
        question = self.select_question()
        item_id = question.get('item_id')
        marking_id = question.get('marking_id')
        question_no = question.get('question_no')
        answer = self.responses.get(item_id, self.responses_default)
        response = self.client.post(f"/api/responses/{item_id}", name='/api/responses/item_id',
                                    params={"r_key": get_random_string()},
                                    json={"session": self.session, "question_no": question_no,
                                          "marking_id": marking_id,
                                          "response": {"RESPONSE": answer}})
        # print(response.json())
        # print(response)

    def on_start(self):
        token = {"sid": "csetest5", "aid": self.assessment_guid, "sto": 120,
                 "type": "stresstest", "stresstest_token": STRESS_TEST_TOKEN}
        token_base64 = base64.b64encode(json.dumps(token).encode()).decode()
        retry_max = 30
        try_count = 0
        while try_count < retry_max:
            try_count += 1
            # 1. inward 로 로그인함.
            response = self.client.get("/inward?token=" + token_base64, name='/inward',
                                       params={"r_key": get_random_string()})
            # print(self.client.cookies.get_dict())
            if response.status_code != 200:
                continue
            time.sleep(15)
            # 2. 시험용 session 값을 받아와 저장
            response = self.client.post("/api/session", name='/api/session',
                                        params={"r_key": get_random_string()},
                                        json={"assessment_guid": self.assessment_guid, "testset_id": self.testset_id,
                                              "student_ip": "123.243.86.1", "start_time": int(time.time()),
                                              "tnc_agree_checked": True}, cookies=self.client.cookies.get_dict())
            if response.status_code != 200:
                continue
            time.sleep(15)
            self.session = response.json().get('data').get('session')

            # 3. test 를 시작하면서 문제를 받아옴.
            response = self.client.post("/api/start", name='/api/start',
                                        params={"r_key": get_random_string()},
                                        json={"session": self.session}, cookies=self.client.cookies.get_dict())
            # print(response.json())
            if response.status_code == 200:
                self.questions = response.json().get('data').get('new_questions')
                try_count = retry_max
                time.sleep(40)

