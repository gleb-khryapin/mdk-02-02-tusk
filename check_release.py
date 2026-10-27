"""Доказательство: в профиле Release вызовов debug нет в байт-коде."""
import dis
import io

from booking.service import BookingService

code = BookingService._book_unsafe.__code__
names = set()
for instr in dis.get_instructions(code):
    if instr.opname in ("LOAD_ATTR", "LOAD_METHOD") and instr.argval:
        names.add(instr.argval)

print("профиль:", "Debug" if __debug__ else "Release", "(__debug__ = %s)" % __debug__)
print("обращения к методам логгера в байт-коде _book_unsafe:",
      sorted(n for n in names if n in {"debug", "info", "warn", "error"}))
print("вызов debug присутствует:", "debug" in names)
