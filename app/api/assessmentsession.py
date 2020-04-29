import copy
import hashlib
from datetime import datetime
from flask import current_app

# from app import cache
from cachelib.filesystemcache import FileSystemCache


class AssessmentSession:
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
        self.cache = FileSystemCache(current_app.config['CACHE_DIR'],
                                     threshold=current_app.config['CACHE_THRESHOLD'],
                                     default_timeout=current_app.config['CACHE_DEFAULT_TIMEOUT'])
        if key is None:
            key_string = '{}:{}:{}:{}'.format(user_id, enroll_id, testset_id, attempt_count)
            self.key = hashlib.sha256(key_string.encode()).hexdigest()
            self.cache.delete(self.key)
            self.assessment = copy.deepcopy(self.assessment_default)
            self.assessment.update({
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

    def save_assessment(self):
        timeout = ((self.get_value('test_duration') + 10) * 60
                   - (int(datetime.now().timestamp()) - self.get_value('start_time')))
        if timeout <= 0:
            return
        self.cache.set(self.key, self.assessment, timeout=timeout)

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
