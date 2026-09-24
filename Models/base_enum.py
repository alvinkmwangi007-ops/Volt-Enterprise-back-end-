"""
models/base_enum.py
A str-Enum base whose __str__ returns the plain value. Without this,
Python's Enum.__str__ returns "ClassName.member_name", which leaks into
marshmallow's JSON output. Every enum in this project should inherit from
StrEnum instead of (str, enum.Enum) directly.
"""

import enum


class StrEnum(str, enum.Enum):
    def __str__(self):
        return self.value
