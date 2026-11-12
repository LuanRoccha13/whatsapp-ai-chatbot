import logging
import httpx
from typing import Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    """
    Serviço responsável pelo envio de mensagens de volta ao WhatsApp.
    Suporta o Gateway Local (Baileys), Evolution API, Z-API e simulação.
    """
    def __init__(self):
        self.gateway_local_url = "http://127.0.0.1:3000/send-message"
        self.base_url = settings.WHATSAPP_API_URL.rstrip("/")
        self.api_key = settings.WHATSAPP_API_KEY
        self.instance = settings.WHATSAPP_INSTANCE_NAME

    async def send_text_message(self, recipient_phone: str, text: str) -> bool:
        """
        Envia mensagem de texto via HTTP POST para a API do WhatsApp.
        Tenta primeiro o Gateway Local (porta 3000), e fallback para a Evolution API.
        """
        clean_phone = "".join(filter(str.isdigit, recipient_phone))

        # 1. Tenta envio pelo Gateway Local Baileys (porta 3000)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    self.gateway_local_url,
                    json={"number": clean_phone, "text": text}
                )
                if res.status_code == 200:
                    logger.info(f"✅ Mensagem enviada pelo Gateway Local para {clean_phone}")
                    return True
        except Exception as e:
            logger.debug(f"Gateway local porta 3000 indisponível: {e}")

        # 2. Se houver Evolution API configurada com API key
        if self.api_key and "localhost:8080" not in self.base_url:
            headers = {
                "Content-Type": "application/json",
                "apikey": self.api_key
            }
            endpoint = f"{self.base_url}/message/sendText/{self.instance}"
            payload = {
                "number": clean_phone,
                "options": {"delay": 1200, "presence": "composing"},
                "textMessage": {"text": text}
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)
                    if response.status_code in [200, 201]:
                        logger.info(f"Mensagem enviada via Evolution API para {clean_phone}")
                        return True
            except Exception as e:
                logger.error(f"Falha na Evolution API: {e}")

        # 3. Log de fallback
        logger.info(f"[WHATSAPP SIMULAÇÃO] Enviado para {clean_phone}: '{text}'")
        return True

whatsapp_service = WhatsAppService()
