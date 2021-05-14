import os

from flask import Flask, g
from flask.sessions import SecureCookieSessionInterface
from flask_bootstrap import Bootstrap
# from flask_caching import Cache
from flask_cors import CORS
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from jinja2.environment import Environment

from config import config
from qti.itemservice.itemservice import ItemService

db = SQLAlchemy()
bootstrap = Bootstrap()
mail = Mail()
# cache = Cache()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
# Dynamic IP: https://flask-login.readthedocs.io/en/latest/
login_manager.session_protection = None
login_manager.login_message = ''


def create_app(config_name):
    app = Flask(__name__)
    if type(config_name) != str:
        config_name = os.getenv('FLASK_CONFIG') or 'default'
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    #CORS(app, supports_credentials=True)
    CORS(app, resources={r'*': {'origins': '*'}})
    #CORS(app, resources={
    #    r"/v1/*": {"origin": "*"},
    #    r"/api/*": {"origin": "*"},
    #})
    db.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    login_manager.init_app(app)

    # cache.init_app(app, {
    #     'CACHE_TYPE': app.config['CACHE_TYPE'],
    #     'CACHE_DEFAULT_TIMEOUT': app.config['CACHE_DEFAULT_TIMEOUT']
    # })

    jinja_env = Environment(extensions=['jinja2.ext.loopcontrols'])
    app.jinja_env.add_extension('jinja2.ext.loopcontrols')

    # Set storage directory for import service.
    ItemService.initialize(app.config['STORAGE_DIR'])

    from .web import web as web_blueprint
    app.register_blueprint(web_blueprint, url_prefix='/')

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')

    from .item import item as item_blueprint
    app.register_blueprint(item_blueprint, url_prefix='/item')

    from .testlet import testlet as testlet_blueprint
    app.register_blueprint(testlet_blueprint, url_prefix='/testlet')

    from .testset import testset as testset_blueprint
    app.register_blueprint(testset_blueprint, url_prefix='/testset')

    from .itemstatic import itemstatic as itemstatic_blueprint
    app.register_blueprint(itemstatic_blueprint, url_prefix='/itemstatic')

    from .assessment import assessment as assessment_blueprint
    app.register_blueprint(assessment_blueprint, url_prefix='/assessment')

    from .report import report as report_blueprint
    app.register_blueprint(report_blueprint, url_prefix='/report')

    from .errornote import errornote as errornote_blueprint
    app.register_blueprint(errornote_blueprint, url_prefix='/errnote')

    from .plan import plan as plan_blueprint
    app.register_blueprint(plan_blueprint, url_prefix='/plan')

    from .writing import writing as writing_blueprint
    app.register_blueprint(writing_blueprint, url_prefix='/writing')

    app.session_interface = CustomSessionInterface()

    # json encoding
    from app.json_encoder import AlchemyEncoder
    app.json_encoder = AlchemyEncoder

    return app


class CustomSessionInterface(SecureCookieSessionInterface):
    """
    Prevent creating session from API requests.
    """

    def save_session(self, *args, **kwargs):
        if g.get('login_via_header'):
            return
        return super(CustomSessionInterface, self).save_session(*args,
                                                                **kwargs)

#
# @login_manager.user_loader
# def load_user(user_id):
#     pass
#
#
# @login_manager.request_loader
# def load_request(request):
#     return None
#
#
# @login_manager.unauthorized_handler
# def unauthorized_handler():
#     pass
