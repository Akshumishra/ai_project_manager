from pydantic import BaseModel
from uuid import UUID

class ChannelMappingBase(BaseModel):
    channel_id: str
    channel_name: str

class ChannelMappingCreate(ChannelMappingBase):
    pass

class ChannelMappingResponse(ChannelMappingBase):
    id: UUID

    class Config:
        orm_mode = True