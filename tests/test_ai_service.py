import pytest
from app.services.memory_service import MemoryService
from app.services.ai_service import AIService

@pytest.fixture
def memory():
    return MemoryService(max_messages=4)

def test_memory_add_and_limit(memory):
    phone = "5511999999999"
    memory.add_message(phone, "user", "Olá")
    memory.add_message(phone, "assistant", "Oi! Como posso ajudar?")
    memory.add_message(phone, "user", "Qual o horário?")
    memory.add_message(phone, "assistant", "Das 9h às 18h.")
    memory.add_message(phone, "user", "Obrigado!")

    history = memory.get_history(phone)
    # Deve conter apenas as 4 últimas mensagens
    assert len(history) == 4
    assert history[-1]["content"] == "Obrigado!"

@pytest.mark.asyncio
async def test_human_takeover_detection():
    service = AIService()
    result = await service.generate_response(
        sender_phone="5511999999999",
        message_text="Quero falar com um atendente humano por favor",
        sender_name="Luan"
    )
    assert result["transferred_to_human"] is True
    assert "atendentes humanos" in result["text"].lower()
