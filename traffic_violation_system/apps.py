from django.apps import AppConfig


class TrafficViolationSystemConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "traffic_violation_system"

    def ready(self):
        import traffic_violation_system.models  # Import the models module to register signals
