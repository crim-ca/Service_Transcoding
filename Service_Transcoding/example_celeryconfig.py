"""
Configuration values for transition process.
"""

BROKER_URL = 'amqp://localhost//'
CELERY_RESULT_BACKEND = 'amqp://'

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

CELERYD_PREFETCH_MULTIPLIER = 1
CELERY_TASK_RESULT_EXPIRES = 7200  # 2 Hours