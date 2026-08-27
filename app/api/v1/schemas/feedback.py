import uuid

from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    feedback_id: str = ""
    session_id: str
    user_id: str | None = None
    message_id: str | None = None
    rating: int
    comment: str | None = None

    def model_post_init(self, __context):
        if not self.feedback_id:
            self.feedback_id = str(uuid.uuid4())


class FeedbackResponse(BaseModel):
    feedback_id: str
    status: str


__all__ = ["FeedbackRequest", "FeedbackResponse"]
