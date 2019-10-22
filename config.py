import os
import shutil

from flask_env import MetaFlaskEnv

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(metaclass=MetaFlaskEnv):
    # import secrets;secrets.token_urlsafe(24)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'YYJ19jTgcUqg1JVjwxGy3Eb_CgHMnzkw'
    DELETE_SECRET_KEY = os.environ.get('DELETE_SECRET_KEY') or '@tRt_3xpNn@V5w-au9B3rnES&8w2Ra2D'
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    CSEDU_MAIL_SUBJECT_PREFIX = '[CSEDU]'
    CSEDU_MAIL_SENDER = 'CSEDU Admin <csedu@example.com>'
    CSEDU_ADMIN = os.environ.get('CSEDU_ADMIN')
    CSEDU_ITEM_PER_PAGE = 25

    # ToDo: Need to update Upload_folder, allowed_extentions
    UPLOAD_FOLDER = os.environ.get('TEMP') or 'tmp/upload'
    ALLOWED_EXTENSIONS = {'xml', 'xls', 'xlsx', 'zip'}

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True

    # log 저장 폴더: LOGS_DIR 환경변수가 지정되지 않으면, 소스 폴더에 logs 폴더를 사용함.
    LOGS_DIR = os.environ.get('LOGS_DIR') or os.path.join(basedir, 'logs')

    # Import용 임시 XML 을 저장하는 폴더. 수시로 purge됨
    IMPORT_TEMP_DIR = os.path.join(basedir, 'import_temp')

    # TEST DATA folder
    DEPLOY_DATA_DIR = os.environ.get('DEPLOY_DATA_DIR') or 'app/deploy'

    # NAPLAN individual Report folder
    NAPLAN_RESULT_DIR = os.environ.get('NAPLAN_RESULT_DIR') or 'app/static/report/naplan_result'

    # QTI XML 을 저장하는 폴더
    STORAGE_DIR = os.path.join(basedir, 'storage')

    # Response processing PHP location
    QTI_RSP_PROCESSING_PHP = os.path.join(basedir, 'rspProcessing/rspProcess.php')

    # Flask-Caching
    CACHE_TYPE = 'filesystem'
    CACHE_DIR = os.path.join(STORAGE_DIR, 'cache')
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 hour

    @classmethod
    def init_app(cls, app):
        # log 저장 폴더가 없으면 생성한다.
        logs_dir = app.config['LOGS_DIR']
        if not os.path.exists(logs_dir):
            os.mkdir(logs_dir)
        import_temp_dir = app.config['IMPORT_TEMP_DIR']
        if os.path.exists(import_temp_dir):
            shutil.rmtree(import_temp_dir, ignore_errors=True)
        os.mkdir(import_temp_dir)
        storage_dir = app.config['STORAGE_DIR']
        if not os.path.exists(storage_dir):
            os.mkdir(storage_dir)
        cache_dir = app.config['CACHE_DIR']
        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)

    # CS_API
    CS_API_URL = os.environ.get('CS_API_URL') or 'https://13.210.98.100:7443/csonlineschool'
    CS_API_USER = "admin@csedu.com"
    CS_API_PASSWORD = "kpKp*oiTokH8"


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://dbuser:P@ssword1@localhost/tailored'
    # SQLALCHEMY_ECHO = True
    # PREFERRED_URL_SCHEME = 'https'


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')
    WTF_CSRF_ENABLED = False
    STORAGE_DIR = os.path.join(basedir, 'test_storage')


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'data.sqlite')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # email errors to the administrators
        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.CSEDU_MAIL_SENDER,
            toaddrs=[cls.CSEDU_ADMIN],
            subject=cls.CSEDU_MAIL_SUBJECT_PREFIX + ' Application Error',
            credentials=credentials,
            secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
