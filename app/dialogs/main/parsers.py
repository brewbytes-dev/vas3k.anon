from dataclasses import dataclass

from app.dataparser import DataParser


@dataclass
class PostCardData(DataParser):
    user_id = None
    username = None
    reply_message_id = None
    message_id = None
    text = None
    medias = None
    content_author = None
    content_type = None
    sent_url = None

    def __post_init__(self):
        self.messages = []
        self.text = []
        self.medias = []
