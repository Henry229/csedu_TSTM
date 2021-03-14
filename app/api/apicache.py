from flask import current_app

from cachelib import RedisCache
from cachelib import FileSystemCache


class ApiCache:
    def __init__(self):
        self._cache = None

    @property
    def cache(self):
        if self._cache is None:
            if current_app.config['RUNNER_SESSION_STORAGE'] == 'redis':
                self._cache = RedisCache(host=current_app.config['CACHE_REDIS_HOST'], key_prefix='api-',
                                         default_timeout=current_app.config['API_RENDERED_CACHE_TIMEOUT'])
            else:
                self._cache = FileSystemCache(current_app.config['CACHE_DIR'],
                                              threshold=current_app.config['CACHE_THRESHOLD'],
                                              default_timeout=current_app.config['API_RENDERED_CACHE_TIMEOUT'])
        return self._cache

    def set(self, key, value, timeout=None):
        self.cache.set(key, value, timeout)

    def get(self, key):
        return self.cache.get(key)

    def delete(self, key):
        self.cache.delete(key)
