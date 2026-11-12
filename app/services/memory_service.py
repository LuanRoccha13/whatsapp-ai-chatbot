from typing import Dict, List, Any
import time

class MemoryService:
    """
    Gerencia o histórico de conversas em memória por número de telefone.
    Permite que o chatbot mantenha o contexto da conversa.
    """
    def __init__(self, max_messages: int = 6):
        self.max_messages = max_messages
        # Structure: { phone_number: [{"role": "user"|"assistant", "content": "...", "timestamp": float}] }
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}

    def get_history(self, phone: str) -> List[Dict[str, str]]:
        """Retorna as mensagens recentes formatadas para o modelo de IA."""
        if phone not in self._conversations:
            return []
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self._conversations[phone]
        ]

    def add_message(self, phone: str, role: str, content: str):
        """Adiciona uma nova mensagem ao histórico do cliente."""
        if phone not in self._conversations:
            self._conversations[phone] = []

        self._conversations[phone].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })

        # Keep only the last `max_messages`
        if len(self._conversations[phone]) > self.max_messages:
            self._conversations[phone] = self._conversations[phone][-self.max_messages:]

    def clear_history(self, phone: str):
        """Limpa o histórico de uma conversa."""
        if phone in self._conversations:
            del self._conversations[phone]

memory_service = MemoryService()
