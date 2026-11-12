import logging
import httpx
from typing import Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    """
    Serviço responsável pelo envio de mensagens de volta ao WhatsApp.
    Suporta Evolution API, Z-API e instâncias auto-hospedadas.
    """
    def __init__(self):
        self.base_url = settings.WHATSAPP_API_URL.rstrip("/")
        self.api_key = settings.WHATSAPP_API_KEY
        self.instance = settings.WHATSAPP_INSTANCE_NAME

    async def send_text_message(self, recipient_phone: str, text: str) -> bool:
        """
        Envia mensagem de texto via HTTP POST para a API do WhatsApp.
        """
        # Limpa o número para conter apenas dígitos
        clean_phone = "".join(filter(str.isdigit, recipient_phone))

        if not self.api_key or "localhost" in self.base_url:
            # Modo simulação local / log
            logger.info(f"[SIMULAÇÃO WHATSAPP] Enviando para {clean_phone}: '{text}'")
            return True

        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

        # Payload padrão compatível com Evolution API
        endpoint = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": clean_phone,
            "options": {
                "delay": 1200,
                "presence": "composing"
            },
            "textMessage": {
                "text": text
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                if response.status_code in [200, 201]:
                    logger.info(f"Mensagem enviada com sucesso para {clean_phone}")
                    return True
                else:
                    logger.error(f"Erro ao enviar para WhatsApp ({response.status_code}): {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Falha de conexão com a API do WhatsApp: {e}")
            return False

whatsapp_service = WhatsAppService()
