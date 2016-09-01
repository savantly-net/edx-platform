"""
Django Application Configuration for course_structures app.
"""
from django.apps import AppConfig


class CourseStructuresConfig(AppConfig):
    """
    Custom AppConfig.  Registers Signals
    """
    name = u'openedx.core.djangoapps.content.course_structures'

    def ready(self):
        from . import signals  # pylint: disable=unused-variable
