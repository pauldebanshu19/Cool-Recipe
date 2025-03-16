from django.db import models
from django_mongodb_backend.fields import ArrayField, EmbeddedModelField
from django_mongodb_backend.managers import MongoManager
from django_mongodb_backend.models import EmbeddedModel


class Features(EmbeddedModel):
    preparation_time = models.CharField(max_length=100)
    complexity = models.CharField(max_length=100)
    prep_time = models.IntegerField()
    cuisine = models.CharField(max_length=100, null=True, blank=True)


class Recipe(models.Model):
    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)
    features = EmbeddedModelField(Features, null=True, blank=True)
    ingredients = ArrayField(models.CharField(max_length=100), null=True, blank=True)
    embedding_ingredients = models.CharField(max_length=500, null=True, blank=True)
    voyage_embedding = models.JSONField(null=True, blank=True)

    objects = MongoManager()

    class Meta:
        db_table = "recipes"
        managed = False

    def __str__(self):
        return f"Recipe {self.title}"
