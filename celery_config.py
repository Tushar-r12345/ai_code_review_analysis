"""
Configures and initializes a Celery application for task management.

Input:
- 'tasks': The name of the Celery app and the module containing task definitions.
- Redis broker URL: 'redis://localhost:6379/0' (Default Redis instance).
- Redis backend URL: 'redis://localhost:6379/0' (Default Redis instance).

Function:
1. Creates a Celery app instance named 'tasks', using Redis as both the message broker and result backend.
2. Enables automatic task discovery within the 'tasks' module/directory, allowing Celery to find and register tasks.
3. Configures various Celery settings:
    a. result_expires: Sets the expiration time for task results to 3600 seconds (1 hour). After this time, results are deleted from the backend.
    b. task_default_retry_delay: Sets the default delay before retrying a failed task to 30 seconds.
    c. task_max_retries: Sets the maximum number of retry attempts for a task to 5.
    d. task_acks_late: Configures tasks to be acknowledged *after* execution, ensuring that tasks are not lost if a worker crashes during processing.

Output:
- app: A fully configured Celery application instance, ready for defining and executing tasks.
"""


from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

app.autodiscover_tasks(['tasks']) 

app.conf.update(
    result_expires=3600,
    task_default_retry_delay=30,
    task_max_retries=5,
    task_acks_late=True,
)

