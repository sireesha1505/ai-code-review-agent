from pydantic import BaseModel

class Repository(BaseModel):
    repository_name:str
    pull_request: str
    sendor: str
    action: str