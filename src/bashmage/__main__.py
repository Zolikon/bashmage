import os
import sys
from bashmage.app import BashMageApp
from bashmage.storage import load_commands


_ZSH_INIT = """\
# BashMage shell integration (zsh)
# Add to ~/.zshrc:  eval "$(bashmage --init)"
_bashmage_widget() {
  local tmp ret cmd saved_stty
  tmp=$(mktemp) || return
  saved_stty=$(stty -g 2>/dev/null)
  bashmage >"$tmp" </dev/tty
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


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        _print_init(sys.argv[2] if len(sys.argv) > 2 else None)
        return

    try:
        commands = load_commands()
    except Exception as e:
        print(f"bashmage: error loading commands: {e}", file=sys.stderr)
        sys.exit(1)

    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    tty_file = None

    try:
        if not sys.stdout.isatty():
            tty_file = open("/dev/tty", "w")
            sys.stdout = tty_file
            sys.stderr = tty_file

        app = BashMageApp(commands)
        result = app.run()
    finally:
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr
        if tty_file is not None:
            tty_file.close()

    if result is not None:
        print(result)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
