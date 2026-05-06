import os
from peewee import *
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "watchtower.db")
db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    class Meta:
        database = db


class Release(BaseModel):
    source = CharField()          # comicvine | tmdb | openlibrary
    category = CharField()        # comics | film | tv | books | manga
    title = CharField()
    description = TextField(null=True)
    release_date = DateField(null=True)
    cover_url = TextField(null=True)
    external_id = CharField(unique=True)
    fetched_at = DateTimeField(default=datetime.utcnow)


class Post(BaseModel):
    release = ForeignKeyField(Release, backref="posts")
    caption = TextField()
    image_path = TextField()
    status = CharField(default="pending")  # pending | posted | failed | dry_run
    instagram_media_id = CharField(null=True)
    posted_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)


def init_db():
    db.connect(reuse_if_open=True)
    db.create_tables([Release, Post], safe=True)
