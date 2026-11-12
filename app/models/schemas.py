from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class IncomingMessage(BaseModel):
    sender_phone: str = Field(..., description="Número de telefone do remetente (com DDI/DDD)")
    sender_name: Optional[str] = Field("Cliente", description="Nome do remetente, se disponível")
    message_text: str = Field(..., description="Texto da mensagem recebida")
    is_group: bool = Field(False, description="Indica se a mensagem veio de um grupo")
    message_id: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None

class OutgoingMessage(BaseModel):
    recipient_phone: str
    message_text: str

class ChatResponse(BaseModel):
    status: str
    recipient_phone: str
    reply_text: str
    transferred_to_human: bool = False
