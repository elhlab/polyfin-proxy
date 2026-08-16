from tortoise import fields
from tortoise.models import Model


class UserPreference(Model):
    id = fields.CharField(max_length=32, primary_key=True)
    language_id = fields.CharField(
        max_length=32, null=True
    )  # Direct reference to the config language. null indicates default. which means to not modify the payload.


# This is no longer needed we can just steal user session as needed
class Token(Model):
    # A SHA-256 hash of the apitoken
    token_hash = fields.CharField(max_length=64, primary_key=True)

    user = fields.ForeignKeyField("models.User", related_name="tokens")


# TODO translate genres
# TODO: look into translating tags

# Note while metadata does not contain season anme labels. this is directly retrived from the config.
# Season name must be replaced by the patch aswell


class Movie(Model):
    id = fields.CharField(max_length=32, primary_key=True)

    name = fields.CharField(max_length=256, null=True)
    overview = fields.TextField(null=True)

    provider_ids = fields.JSONField(null=True)


class Show(Model):
    id = fields.CharField(max_length=32, primary_key=True)

    name = fields.CharField(max_length=256, null=True)
    overview = fields.TextField(null=True)

    provider_ids = fields.JSONField(null=True)
    # eg {"imdb": tt592392, "tvdb": 5436373}


class Season(Model):
    id = fields.CharField(max_length=32, primary_key=True)

    show = fields.ForeignKeyField("models.Show", related_name="seasons")

    name = fields.CharField(max_length=256, null=True)
    overview = fields.TextField(null=True)

    provider_ids = fields.JSONField(null=True)


class Episode(Model):
    id = fields.CharField(max_length=32, primary_key=True)

    season = fields.ForeignKeyField("models.Season", related_name="episodes")

    name = fields.CharField(max_length=256, null=True)
    overview = fields.TextField(null=True)

    provider_ids = fields.JSONField(null=True)
