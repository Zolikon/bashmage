from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView

from bashmage.storage import Command


class CommandItem(ListItem):
    def __init__(self, command: Command) -> None:
        super().__init__()
        self.command = command

    def compose(self) -> ComposeResult:
        name_part = (
            f"{self.command.name} [bold][[{self.command.shortcut}]][/bold]"
            if self.command.shortcut
            else self.command.name
        )
        yield Label(f"{name_part}\n[dim]{self.command.description}[/dim]")


class CommandList(Widget):
    DEFAULT_CSS = """
    CommandList {
        width: 1fr;
        border-right: solid $primary;
    }
    CommandList ListView {
        height: 1fr;
    }
    """

    class Highlighted(Message):
        def __init__(self, command: Command) -> None:
            super().__init__()
            self.command = command

    class Selected(Message):
        def __init__(self, command: Command) -> None:
            super().__init__()
            self.command = command

    def __init__(self, commands: list[Command]) -> None:
        super().__init__()
        self._all_commands = commands
        self._filtered = list(commands)

    def compose(self) -> ComposeResult:
        yield ListView(*[CommandItem(c) for c in self._all_commands])

    EMPTY_MESSAGE = "(no commands)"
    NO_MATCH_MESSAGE = "(no matches)"

    def filter(self, query: str) -> None:
        tokens = query.lower().split()
        text_tokens = [t for t in tokens if not t.startswith("#")]
        tag_tokens = [t[1:] for t in tokens if t.startswith("#") and len(t) > 1]

        def matches(c: Command) -> bool:
            for t in text_tokens:
                if (
                    t not in c.name.lower()
                    and t not in c.description.lower()
                    and (c.shortcut is None or t not in c.shortcut.lower())
                ):
                    return False
            for t in tag_tokens:
                if not any(t in tag.lower() for tag in c.tags):
                    return False
            return True

        self._filtered = [c for c in self._all_commands if not tokens or matches(c)]
        lv = self.query_one(ListView)
        lv.clear()
        if self._filtered:
            for cmd in self._filtered:
                lv.append(CommandItem(cmd))
        else:
            msg = self.NO_MATCH_MESSAGE if tokens else self.EMPTY_MESSAGE
            lv.append(ListItem(Label(f"[dim]{msg}[/dim]")))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, CommandItem):
            self.post_message(self.Highlighted(event.item.command))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, CommandItem):
            self.post_message(self.Selected(event.item.command))
