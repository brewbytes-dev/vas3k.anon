from dataclasses import dataclass

from app.dataparser import DataParser


@dataclass
class PostCardData(DataParser):
    user_id = None
    username = None
    reply_message_id = None
    message_id = None
    text = None
    photos = None

    def __post_init__(self):
        self.messages = []
        self.text = []
        self.photos = []
