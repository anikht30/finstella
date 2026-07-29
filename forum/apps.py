from django.apps import AppConfig


class ForumConfig(AppConfig):
    name = 'forum'

    def ready(self):
        # this tell django to wake up the signal listner
        import forum.signals
