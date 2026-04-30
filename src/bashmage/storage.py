import re
from dataclasses import dataclass


@dataclass
class Command:
    name: str
    description: str
    command: str

    @property
    def placeholders(self) -> list[str]:
        return list(dict.fromkeys(re.findall(r'\{(\w+)\}', self.command)))

    def fill(self, values: dict[str, str]) -> str:
        result = self.command
        for key, value in values.items():
            result = result.replace(f'{{{key}}}', value)
        return result
