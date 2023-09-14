from pydantic import BaseModel


class MessageRequest(BaseModel):
    __message: str

    def get_message(self):
        return self.__message
