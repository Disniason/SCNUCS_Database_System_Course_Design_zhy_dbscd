from pydantic import BaseModel



class SendCodeReq(BaseModel):
    email: str

class VerifyCodeReq(BaseModel):
    email: str
    code: str

class FinishRegisterReq(BaseModel):
    email: str
    encrypted_password: str

class FeedbackPublishBody(BaseModel):
    content: str



