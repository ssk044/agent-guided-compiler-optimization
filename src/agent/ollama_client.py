"""
Client interface for local Ollama LLM execution with structured JSON response guarantees.
"""
import json
import logging
import signal
from typing import Optional, List, Dict, Any

try:
    import ollama
except ImportError:
    ollama = None

logger = logging.getLogger(__name__)


class OllamaClient:
    PREFERRED_MODELS = [
        "qwen2.5-coder:3b",
        "qwen2.5-coder:latest",
        "qwen2.5:3b",
        "qwen2.5:latest",
        "tinyllama:latest"
    ]

    def __init__(self, requested_model: Optional[str] = None, host: Optional[str] = None):
        self.requested_model = requested_model
        self.host = host
        self.active_model: Optional[str] = None
        self._resolve_model()

    def _resolve_model(self):
        if not ollama:
            logger.warning("Ollama Python package is not installed.")
            return

        try:
            client = ollama.Client(host=self.host) if self.host else ollama
            model_list = client.list()
            available = []
            for m in model_list.get("models", []):
                name = m.get("name") or m.get("model") or ""
                if name:
                    available.append(name)

            if self.requested_model:
                # Check exact or prefix match
                for av in available:
                    if self.requested_model in av:
                        self.active_model = av
                        return
                self.active_model = self.requested_model
                return

            # Check preferred models in priority order
            for pref in self.PREFERRED_MODELS:
                for av in available:
                    if pref in av:
                        self.active_model = av
                        return

            if available:
                self.active_model = available[0]
            else:
                self.active_model = "qwen2.5-coder:3b"
        except Exception as e:
            logger.warning(f"Could not connect to Ollama daemon: {e}. Using fallback default.")
            self.active_model = self.requested_model or "qwen2.5-coder:3b"

    def is_available(self) -> bool:
        if not ollama:
            return False
        try:
            client = ollama.Client(host=self.host) if self.host else ollama
            client.list()
            return True
        except Exception:
            return False

    def generate_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Calls Ollama with JSON mode enforced and parses the output.
        """
        if not ollama:
            raise RuntimeError("Ollama library not installed")

        client = ollama.Client(host=self.host) if self.host else ollama
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # A local model must never block the compiler workflow indefinitely.
        def expired(signum, frame):
            raise TimeoutError("Ollama inference exceeded the 45-second limit")

        previous_handler = signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, 20)
        try:
            response = client.chat(
                model=self.active_model,
                messages=messages,
                format="json",
                options={"temperature": temperature, "num_predict": 250}
            )
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)

        content = response["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback regex extraction if wrapped in markdown
            import re
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise ValueError(f"Failed to parse LLM response as JSON: {content}")
