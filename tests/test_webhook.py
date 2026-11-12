import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"

@pytest.mark.asyncio
async def test_direct_chat_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "sender_phone": "5511999999999",
            "sender_name": "Luan",
            "message_text": "Olá, quais serviços vocês oferecem?"
        }
        response = await client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["reply_text"]) > 0

@pytest.mark.asyncio
async def test_webhook_ignore_bot_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "data": {
                "key": {
                    "fromMe": True,
                    "remoteJid": "5511999999999@s.whatsapp.net"
                }
            }
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
