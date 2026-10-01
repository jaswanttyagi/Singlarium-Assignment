from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):

    @abstractmethod
    async def enrich(self, raw_title, raw_description=""):
        pass