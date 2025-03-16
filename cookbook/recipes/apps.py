from django.apps import AppConfig


class RecipesConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "recipes"
