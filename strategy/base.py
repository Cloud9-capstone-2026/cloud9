from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def calculate_signal(self, prices: list) -> str | None:
        pass