import logging
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.schemas import IncomingMessage, ChatResponse, OutgoingMessage
from app.services.ai_service import ai_service
from app.services.whatsapp_service import whatsapp_service
from app.services.memory_service import memory_service

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("whatsapp-bot")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend de Automação para Chatbot no WhatsApp integrado com IA Generativa."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "ai_provider": settings.AI_PROVIDER,
        "docs_url": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint principal receptor de Webhook do WhatsApp.
    Suporta Evolution API, Z-API e payloads estruturados.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Corpo da requisição JSON inválido.")

    logger.info(f"Webhook recebido: {body}")

    # Extração inteligente de dados (compatível com Evolution API e Z-API)
    sender_phone = None
    sender_name = "Cliente"
    message_text = None
    is_group = False

    # 1. Padrão Evolution API v1 e v2
    if "data" in body and isinstance(body["data"], dict):
        data = body["data"]
        key = data.get("key", {})
        
        # Ignora mensagens enviadas pelo próprio bot
        if key.get("fromMe", False):
            return {"status": "ignored", "reason": "sent_by_bot"}

        remote_jid = key.get("remoteJid", "")
        if "@g.us" in remote_jid:
            is_group = True
            
        sender_phone = remote_jid.split("@")[0]
        sender_name = data.get("pushName") or "Cliente"

        # Extrai mensagem de texto
        message_obj = data.get("message", {})
        message_text = (
            message_obj.get("conversation") or
            message_obj.get("extendedTextMessage", {}).get("text")
        )

    # 2. Padrão Z-API ou Webhook Direto
    elif "phone" in body and "text" in body:
        sender_phone = body.get("phone")
        sender_name = body.get("senderName", "Cliente")
        message_text = body.get("text", {}).get("message") if isinstance(body.get("text"), dict) else body.get("text")
        is_group = body.get("isGroup", False)

    # 3. Payload customizado direto
    elif "sender_phone" in body and "message_text" in body:
        sender_phone = body.get("sender_phone")
        sender_name = body.get("sender_name", "Cliente")
        message_text = body.get("message_text")

    # Valida se há conteúdo para processar
    if not sender_phone or not message_text:
        return {"status": "ignored", "reason": "no_valid_text_or_sender"}

    if is_group:
        return {"status": "ignored", "reason": "group_messages_disabled"}

    # Processamento em background para responder rápido ao webhook do WhatsApp
    background_tasks.add_task(
        process_and_reply,
        sender_phone=sender_phone,
        message_text=message_text,
        sender_name=sender_name
    )

    return {"status": "received", "sender": sender_phone}


async def process_and_reply(sender_phone: str, message_text: str, sender_name: str):
    """Gera a resposta com a IA e despacha para o WhatsApp do cliente."""
    try:
        ai_result = await ai_service.generate_response(
            sender_phone=sender_phone,
            message_text=message_text,
            sender_name=sender_name
        )

        reply_text = ai_result["text"]
        await whatsapp_service.send_text_message(sender_phone, reply_text)

        if ai_result.get("transferred_to_human"):
            logger.warning(f"🚨 Atendimento de {sender_phone} transferido para atendente humano.")
    except Exception as e:
        logger.error(f"Erro ao processar resposta: {e}", exc_info=True)


@app.post("/api/chat", response_model=ChatResponse)
async def direct_chat_test(payload: IncomingMessage):
    """
    Endpoint para testar a IA diretamente (via Swagger / cURL / Postman)
    sem precisar de uma conexão ativa com o WhatsApp.
    """
    ai_result = await ai_service.generate_response(
        sender_phone=payload.sender_phone,
        message_text=payload.message_text,
        sender_name=payload.sender_name
    )

    return ChatResponse(
        status="success",
        recipient_phone=payload.sender_phone,
        reply_text=ai_result["text"],
        transferred_to_human=ai_result.get("transferred_to_human", False)
    )


@app.get("/api/faq")
async def get_faq():
    """Retorna a base de conhecimento atual do assistente."""
    return JSONResponse(content=ai_service.knowledge_base)
