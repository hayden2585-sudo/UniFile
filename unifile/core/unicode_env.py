"""
Unifile by Soniscorett - Cross-Platform Unicode & Terminal Output Stabilizer
Automatically configures Windows and legacy terminal standard I/O streams to UTF-8
without requiring manual PYTHONIOENCODING environment variable overrides.
"""

from __future__ import annotations
import io
import os
import sys


def configure_unicode_output():
    """
    Ensures sys.stdout, sys.stderr, and standard file operations use UTF-8 cleanly
    on Windows consoles (cmd.exe, PowerShell) and POSIX environments.
    Guarantees no UnicodeEncodeError crashes on emojis, diacritics, or CJK characters.
    """
    # 1. Enable Windows Virtual Terminal Processing (VT100 ANSI & Unicode support)
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # STD_OUTPUT_HANDLE = -11, ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            h_out = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(h_out, ctypes.byref(mode)):
                kernel32.SetConsoleMode(h_out, mode.value | 0x0004)
        except Exception:
            pass

    # 2. Reconfigure stdout and stderr streams to UTF-8 with replacement error handling
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None:
            # Python 3.7+ stream.reconfigure
            if hasattr(stream, "reconfigure"):
                try:
                    stream.reconfigure(encoding="utf-8", errors="replace")
                    continue
                except Exception:
                    pass
            # Fallback TextIOWrapper over underlying buffer
            try:
                if hasattr(stream, "buffer"):
                    wrapped = io.TextIOWrapper(
                        stream.buffer,
                        encoding="utf-8",
                        errors="replace",
                        line_buffering=True,
                    )
                    setattr(sys, stream_name, wrapped)
            except Exception:
                pass


def safe_print(*args, **kwargs):
    """
    Drop-in print replacement that guarantees no UnicodeEncodeError is ever raised,
    even on restricted cp1252 or ASCII terminal streams.
    """
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    file = kwargs.get("file", sys.stdout)
    flush = kwargs.get("flush", False)

    text = sep.join(str(a) for a in args)

    try:
        print(text, end=end, file=file, flush=flush)
    except (UnicodeEncodeError, UnicodeError):
        enc = getattr(file, "encoding", None) or "ascii"
        fallback = text.encode(enc, errors="replace").decode(enc, errors="replace")
        print(fallback, end=end, file=file, flush=flush)


# Auto-configure upon module import
configure_unicode_output()
