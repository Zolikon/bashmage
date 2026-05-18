import os
import sys
from pathlib import Path
from textual.app import App
from bashmage.app import BashMageApp
from bashmage.app_placeholder import PlaceholderApp
from bashmage.context import load_context_commands
from bashmage.storage import Command, load_commands


_ZSH_INIT = """\
# BashMage shell integration (zsh)
# Add to ~/.zshrc:  eval "$(bashmage --init)"
_bashmage_widget() {
  local tmp ret cmd saved_stty
  tmp=$(mktemp) || return
  saved_stty=$(stty -g 2>/dev/null)
  command bashmage >"$tmp" </dev/tty
  ret=$?
  [[ -n "$saved_stty" ]] && stty "$saved_stty" 2>/dev/null
  cmd=$(<"$tmp")
  rm -f "$tmp"
  zle reset-prompt
  [[ $ret -eq 0 && -n "$cmd" ]] || return
  BUFFER="$cmd"
  CURSOR=${#BUFFER}
  zle redisplay
}
zle -N _bashmage_widget
bindkey '^b' _bashmage_widget
bashmage() {
  if [[ $# -eq 0 ]] || [[ "$1" == --* ]]; then
    command bashmage "$@"
    return
  fi
  local tmp cmd
  tmp=$(mktemp) || return
  command bashmage "$@" >"$tmp"
  local ret=$?
  cmd=$(<"$tmp")
  rm -f "$tmp"
  [[ $ret -eq 0 && -n "$cmd" ]] || return
  print -z -- "$cmd"
}
alias bm='bashmage'
"""

_BASH_INIT = """\
# BashMage shell integration (bash)
# Add to ~/.bashrc:  eval "$(bashmage --init)"
_bashmage_widget() {
  local cmd
  cmd=$(bashmage)
  [[ $? -eq 0 && -n "$cmd" ]] || return
  READLINE_LINE="$cmd"
  READLINE_POINT=${#cmd}
}
bind -x '"\\C-b": _bashmage_widget'
"""


def _print_init(shell: str | None) -> None:
    if shell is None:
        shell_path = os.environ.get("SHELL", "")
        if "zsh" in shell_path:
            shell = "zsh"
        elif "bash" in shell_path:
            shell = "bash"
        else:
            print(
                "bashmage: cannot detect shell. "
                "Run: bashmage --init bash  or  bashmage --init zsh",
                file=sys.stderr,
            )
            sys.exit(1)

    if shell == "zsh":
        print(_ZSH_INIT, end="")
    elif shell == "bash":
        print(_BASH_INIT, end="")
    else:
        print(f"bashmage: unknown shell '{shell}'. Supported: bash, zsh", file=sys.stderr)
        sys.exit(1)


def _find_by_shortcut(commands: list[Command], query: str) -> Command | None:
    for cmd in commands:
        if cmd.shortcut == query:
            return cmd
    return None


def _run_app(app: App[str | None]) -> str | None:
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    saved_stdout_fd = None
    try:
        if not sys.stdout.isatty():
            tty_fd = os.open("/dev/tty", os.O_RDWR)
            saved_stdout_fd = os.dup(1)
            os.dup2(tty_fd, 1)
            os.close(tty_fd)
            sys.stdout = open(1, "w", closefd=False)
            sys.stderr = sys.stdout
        return app.run()
    finally:
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr
        if saved_stdout_fd is not None:
            os.dup2(saved_stdout_fd, 1)
            os.close(saved_stdout_fd)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        _print_init(sys.argv[2] if len(sys.argv) > 2 else None)
        return

    try:
        global_commands = load_commands()
    except Exception as e:
        print(f"bashmage: error loading commands: {e}", file=sys.stderr)
        sys.exit(1)

    context_commands = load_context_commands(Path.cwd())
    commands = context_commands + global_commands

    query = sys.argv[1] if len(sys.argv) > 1 else None

    if query is not None:
        match = _find_by_shortcut(commands, query)
        if match is not None:
            if not match.placeholders:
                print(match.command)
                sys.exit(0)
            else:
                result = _run_app(PlaceholderApp(match))
                if result is not None:
                    print(result)
                    sys.exit(0)
                sys.exit(1)

    result = _run_app(BashMageApp(commands, initial_query=query or ""))
    if result is not None:
        print(result)
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
