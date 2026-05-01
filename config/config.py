"""Central configuration values for the music subscription app.

All AWS resource names live here so the three backends and the init scripts
agree on the same names. Override via environment variables when needed.
"""
import os

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

LOGIN_TABLE = os.environ.get("LOGIN_TABLE", "login")
MUSIC_TABLE = os.environ.get("MUSIC_TABLE", "music")

MUSIC_TITLE_GSI = "title-artist-index"
MUSIC_YEAR_LSI = "artist-year-index"

S3_BUCKET = os.environ.get("S3_BUCKET", "as2-music-artist-images")
S3_PRESIGN_TTL = int(os.environ.get("S3_PRESIGN_TTL", "3600"))

SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-only-change-me")
SESSION_TTL_SECONDS = 60 * 60 * 8

LAB_ROLE_NAME = "LabRole"
