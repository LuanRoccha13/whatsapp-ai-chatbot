import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.config import settings
from app.services.memory_service import memory_service

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self) -> str:
        kb_path = Path(__file__).resolve().parent.parent / "data" / "knowledge_base.json"
        if kb_path.exists():
            try:
                with open(kb_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return json.dumps(data, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Erro ao carregar knowledge_base.json: {e}")
        return "{}"

    def build_system_prompt(self, sender_name: Optional[str] = "Cliente") -> str:
        return f"""Você é o Assistente Virtual Oficial da empresa descrita na Base de Conhecimento abaixo.
Seu objetivo é atender clientes no WhatsApp de forma ágil, educada, empática e prestativa.

### DIRETRIZES ESSENCIAIS DE ATENDIMENTO:
1. **Formato WhatsApp:** Suas respostas devem ser curtas e objetivas (máximo de 2 a 4 parágrafos pequenos). Evite blocos gigantes de texto.
2. **Uso de Emojis:** Use emojis moderados para tornar o atendimento simpático e moderno.
3. **Fidelidade à Empresa:** Responda estritamente com base nas informações da empresa fornecidas abaixo.
4. **Limites e Transbordo Humano:** Se o cliente pedir para falar com uma pessoa, atendente humano ou se a dúvida for algo não coberto na base, responda cordialmente informando que você vai transferir o atendimento para um especialista humano da equipe e inclua a tag [HUMAN_TAKEOVER].
5. **Nome do Cliente:** Trate o cliente por '{sender_name}' caso seja apropriado.

### BASE DE CONHECIMENTO DA EMPRESA:
{self.knowledge_base}
"""

    async def generate_response(
        self,
        sender_phone: str,
        message_text: str,
        sender_name: Optional[str] = "Cliente"
    ) -> Dict[str, Any]:
        """
        Gera a resposta da IA utilizando o provedor configurado (Gemini ou OpenAI).
        """
        # Verifica se o cliente pediu diretamente atendente humano
        if any(trigger in message_text.lower() for trigger in ["atendente", "falar com humano", "pessoa real", "suporte humano"]):
            return {
                "text": "Com certeza! Estou transferindo você agora para um de nossos atendentes humanos. Um momento, por favor! ⏳👨‍💻",
                "transferred_to_human": True
            }

        history = memory_service.get_history(sender_phone)
        system_prompt = self.build_system_prompt(sender_name)

        reply_text = ""
        transferred = False

        if settings.AI_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            reply_text = await self._call_openai(system_prompt, history, message_text)
        elif settings.GEMINI_API_KEY:
            reply_text = await self._call_gemini(system_prompt, history, message_text)
        else:
            # Fallback mock response for testing without API keys
            reply_text = (
                f"Olá, {sender_name}! 👋 Recebi sua mensagem: '{message_text}'. "
                f"Sou o assistente inteligente da TechSolutions. "
                f"Para ativar minhas respostas com IA em tempo real, configure sua GEMINI_API_KEY ou OPENAI_API_KEY no arquivo .env!"
            )

        if "[HUMAN_TAKEOVER]" in reply_text:
            reply_text = reply_text.replace("[HUMAN_TAKEOVER]", "").strip()
            transferred = True

        # Atualiza a memória da conversa
        memory_service.add_message(sender_phone, "user", message_text)
        memory_service.add_message(sender_phone, "assistant", reply_text)

        return {
            "text": reply_text,
            "transferred_to_human": transferred
        }

    async def _call_gemini(self, system_prompt: str, history: List[Dict[str, str]], message: str) -> str:
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            # Format contents for Gemini
            contents = [f"INSTRUÇÃO DO SISTEMA:\n{system_prompt}\n"]
            for h in history:
                contents.append(f"{h['role'].upper()}: {h['content']}")
            contents.append(f"USER: {message}")

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents="\n\n".join(contents),
            )
            return response.text or "Desculpe, não consegui processar a resposta no momento."
        except Exception as e:
            logger.error(f"Erro na chamada Gemini: {e}")
            return "Desculpe, tive uma instabilidade momentânea ao processar sua dúvida. Pode repetir?"

    async def _call_openai(self, system_prompt: str, history: List[Dict[str, str]], message: str) -> str:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            messages = [{"role": "system", "content": system_prompt}]
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": message})

            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=350
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Erro na chamada OpenAI: {e}")
            return "Desculpe, tive uma instabilidade momentânea ao processar sua dúvida. Pode repetir?"

ai_service = AIService()
