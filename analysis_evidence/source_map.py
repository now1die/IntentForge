"""Convert Python source offsets to bytes and Monaco positions."""
from bisect import bisect_right
import re

from .contract import Position, Span


class SourceMap:
    def __init__(self, source: str, file: str):
        self.file = file
        self.lines = [0, *(end.end() for end in re.finditer(r"\r\n|\r|\n", source))]
        self.byte_offsets = [0]
        self.utf16_offsets = [0]
        for char in source:
            self.byte_offsets.append(self.byte_offsets[-1] + len(char.encode()))
            self.utf16_offsets.append(self.utf16_offsets[-1] + (2 if ord(char) > 0xFFFF else 1))

    def position(self, offset: int) -> Position:
        line = bisect_right(self.lines, offset)
        column = self.utf16_offsets[offset] - self.utf16_offsets[self.lines[line - 1]] + 1
        return Position(line=line, column=column, byte_offset=self.byte_offsets[offset])

    def span(self, value) -> Span | None:
        if value is None:
            return None
        start, end = value.start.offset, value.end.offset
        if not 0 <= start <= end < len(self.byte_offsets):
            return None
        return Span(file=self.file, start=self.position(start), end=self.position(end))
