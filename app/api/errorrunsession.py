import copy
from datetime import datetime
import pytz
from flask import current_app

# from app import cache
from cachelib.filesystemcache import FileSystemCache

FIXED_CACHE_TIME = 3000  # 50 min


class ErrorRunSession:
    STATUS_READY = 'ready'
    STATUS_IN_TESTING = 'in_testing'
    STATUS_STAGE_FINISHED = 'stage_finished'
    STATUS_TEST_FINISHED = 'test_finished'
    STATUS_TEST_SUBMITTED = 'test_submitted'

    assessment_default = {
        'assessment_enroll_id': 0,
        'attempt_count': 0,
        'testset_id': 0,
        'status': STATUS_READY,
        'stage_data': [],
        'test_items': [],
        'test_duration': 50
    }

    def __init__(self, user_id=0, enroll_id=0, testset_id=0, duration=50, attempt_count=0, key=None):
        """
        AssessmentSession can be created with only key.
        Or other parameters are used to generate a key.
        :param user_id:
        :param enroll_id:
        :param testset_id:
        :param attempt_count:
        :param key:
        """
        self.error_code = None
        self.error_message = None
        self.cache = FileSystemCache(current_app.config['CACHE_DIR'],
                                     threshold=current_app.config['CACHE_THRESHOLD'],
                                     default_timeout=current_app.config['CACHE_DEFAULT_TIMEOUT'])
        if key is None:
            self.key = self.generate_key_string(user_id, enroll_id, testset_id, attempt_count)
            self.cache.delete(self.key)
            self.assessment = copy.deepcopy(self.assessment_default)
            self.assessment.update({
                'user_id': user_id,
                'assessment_enroll_id': enroll_id,
                'attempt_count': attempt_count,
                'testset_id': testset_id,
                'test_duration': duration,
                'status': self.STATUS_READY,
                'start_time': int(datetime.now().timestamp())
            })
            self.save_assessment()
        else:
            self.key = key
            self.assessment = self.cache.get(self.key)
            if self.assessment is not None:
                # To just update session time
                self.save_assessment()

    def reset(self, user_id, enroll_id, testset_id, duration, attempt_count, start_time):
        self.assessment = copy.deepcopy(self.assessment_default)
        self.assessment.update({
            'user_id': user_id,
            'assessment_enroll_id': enroll_id,
            'attempt_count': attempt_count,
            'testset_id': testset_id,
            'test_duration': duration,
            'status': self.STATUS_IN_TESTING,
            'start_time': int(start_time.replace(tzinfo=pytz.UTC).timestamp())
        })

    def save_assessment(self):
        # timeout = ((self.get_value('test_duration') + 10) * 60
        #            - (int(datetime.now().timestamp()) - self.get_value('start_time')))
        # if timeout <= 0:
        #     return
        self.cache.set(self.key, self.assessment, timeout=FIXED_CACHE_TIME)

    def get_assessment(self):
        return self.assessment

    def get_value(self, name):
        return self.assessment.get(name)

    def set_value(self, name, value):
        self.assessment[name] = value
        self.save_assessment()

    def set_status(self, status):
        self.set_value('status', status)

    def get_status(self):
        return self.get_value('status')

    def set_saved_answer(self, marking_id, answer):
        for item in self.assessment['test_items']:
            if item['marking_id'] == marking_id:
                item['saved_answer'] = answer
                self.save_assessment()
                break

    def change_session_key(self):
        old_key = self.key
        self.key = self.generate_key_string(self.assessment['user_id'], self.assessment['assessment_enroll_id'],
                                            self.assessment['testset_id'], self.assessment['attempt_count'])
        self.save_assessment()
        # delete old cache
        self.cache.delete(old_key)
        return self.key

    def set_error(self, error_code, error_message):
        self.error_code = error_code
        self.error_message = error_message

    @staticmethod
    def generate_key_string(user_id, enroll_id, testset_id, attempt_count):
        """
        Cache key 로 사용할 random 문자열을 생성합니다.
        형식은 random_string:enroll_id 로 해서 session key 로부터 enroll id 를 바로 알아낼 수 있도록 합니다.
        최종 session key 는 base64 로 encoding 해서 return 합니다.
        """
        import base64
        import random
        import string
        import hashlib
        key_base = '{}:{}:{}:{}:{}'.format(user_id, enroll_id, testset_id, attempt_count,
                                           random.choices(string.ascii_lowercase + string.digits, k=24))
        hashed_string = hashlib.sha256(key_base.encode()).hexdigest()
        key_string = '{}:{}'.format(hashed_string, enroll_id)
        return base64.urlsafe_b64encode(key_string.encode()).decode()

    @staticmethod
    def enrol_id_from_session_key(session_key):
        import base64
        key_string = base64.urlsafe_b64decode(session_key.encode()).decode()
        enroll_id = key_string.split(':')[1]
        return int(enroll_id)
