import base64
import os

os.environ.setdefault(
    "DATA_ENCRYPTION_KEY",
    base64.urlsafe_b64encode(b"factory-ticket-bot-test-key-0001").decode("ascii"),
)
