from django.apps import AppConfig

class ApplicationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Applications"

    def ready(self):
        import Applications.signals



# class ApplicationsConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'Applications'

