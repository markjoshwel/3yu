"""
3yu.frontend: parser and analyser for 3yu
--------------------------------------------------------------
with all my heart, mark joshwel <mark@joshwel.co> 2024

This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <http://unlicense.org/>
"""

from enum import Enum
from typing import NamedTuple


class TyuUnits(Enum):
    COMMENT = 0
    SCOPE = 1
    DECLARATION = 2
    ASSIGNMENT = 3
    INCLUDE = 4
    IF = 5
    CALL = 6
    RETURN = 7
    ADD = 8
    CONCAT = 9
    SUB = 10
    MUL = 11
    DIV = 12
    MOD = 13
    LSHIFT = 14
    RSHIFT = 15
    SUBSET = 16
    EQ = 17
    LT = 18
    GT = 19
    LTE = 20
    GTE = 21
    AND = 22
    OR = 23
    NOT = 24
    XOR = 25
    BAND = 26
    BOR = 27
    BNOT = 28
    BXOR = 29


class TyuSubUnit(Enum):
    TEXT = 0  # any text until the next unit's character as a delimiter
    REGISTER = 1  # any text until "~" OR a "#" followed by an integer
    VALUE = 2  # integer or rational number, string, list or a scope
    SCOPE = 3
    SCOPE_INNARD = 4  # any text until the next unit's character as a delimiter
    TYPE = 5  # N, I, R, C, S, L<int size><type>, F<argument type><return type>
    ENDING = 6  # "~" or "\n"


class TyuPrimitiveType(Enum):
    NUMERIC = "N"
    INTEGER = "I"
    RATIONAL = "R"
    CONTAINER = "C"
    STRING = "S"
    LIST = "L"
    FUNCTION = "F"


class TyuType(NamedTuple):
    type: TyuPrimitiveType
    inner: "TyuType"


UNIT_SYNTAXES: dict[TyuUnits, tuple[str, TyuSubUnit, str | TyuSubUnit]] = {
    # | declaration/directive | 1st subunit | 2nd subunit                       | 3rd subunit                       |
    # | --------------------- | ----------- | --------------------------------- | --------------------------------- |
    # | comment               | `\`         | comment text                      | `\` or newline                    |
    # | scope declaration     | `(`         | scope instructions                | `)`                               |
    # | register declaration  | `r`         | name (see below for restrictions) | type, see [types](#types)         |
    # | assignment            | `:`         | target register                   | incoming register, value or scope |
    # | include directive     | `#`         | file path                         | `~`                               |
    TyuUnits.COMMENT: ("\\", TyuSubUnit.TEXT, "\\"),
    TyuUnits.SCOPE: ("(", TyuSubUnit.SCOPE_INNARD, ")"),
    TyuUnits.DECLARATION: ("r", TyuSubUnit.TEXT, TyuSubUnit.TYPE),
    TyuUnits.ASSIGNMENT: (":", TyuSubUnit.REGISTER, TyuSubUnit.VALUE),
    TyuUnits.INCLUDE: ("#", TyuSubUnit.TEXT, "~"),
    # | control instruction | 1st subunit | 2nd subunit                       | 3rd subunit                        |
    # | ------------------- | ----------- | --------------------------------- | ---------------------------------- |
    # | if                  | `?`         | register, value or scope          | scope                              |
    # | function call       | `@`         | function or register name, or `!` | register for argument, `_` if none |
    # | return              | `` ` ``     | register                          | `` ` ``                            |
    TyuUnits.IF: ("?", TyuSubUnit.VALUE, TyuSubUnit.SCOPE),
    TyuUnits.CALL: ("@", TyuSubUnit.TEXT, TyuSubUnit.REGISTER),
    TyuUnits.RETURN: ("`", TyuSubUnit.VALUE, "`"),
    # | mathematical operator | 1st subunit | 2nd subunit              | 3rd subunit              |
    # | --------------------- | ----------- | ------------------------ | ------------------------ |
    # | addition              | `+`         | value or register (`NC`) | value or register (`NE`) |
    # | concatenation         | `,`         | value or register (`IC`) | value or register (`IC`) |
    # | subtraction           | `-`         | value or register (`N`)  | value or register (`N`)  |
    # | multiplication        | `*`         | value or register (`NC`) | value or register (`NI`) |
    # | division              | `/`         | value or register (`N`)  | value or register (`N`)  |
    # | modulo                | `%`         | value or register (`N`)  | value or register (`N`)  |
    # | bitshift left         | `l`         | value or register (`NS`) | value or register (`II`) |
    # | bitshift right        | `r`         | value or register (`NS`) | value or register (`II`) |
    TyuUnits.ADD: ("+", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.CONCAT: (",", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.SUB: ("-", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.MUL: ("*", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.DIV: ("/", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.MOD: ("%", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.LSHIFT: ("l", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.RSHIFT: ("r", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    # | relational operator     | 1st subunit | 2nd subunit              | 3rd subunit              |
    # | ----------------------- | ----------- | ------------------------ | ------------------------ |
    # | equals                  | `=`         | value or register        | value or register        |
    # | less than               | `<`         | value or register (`N`)  | value or register (`N`)  |
    # | greater than            | `>`         | value or register (`N`)  | value or register (`N`)  |
    # | less than or equal      | `[`         | value or register (`N`)  | value or register (`N`)  |
    # | greater than or eq      | `]`         | value or register (`N`)  | value or register (`N`)  |
    # | proper subset/inclusion | `c`         | value or register (`EE`) | value or register (`CC`) |
    TyuUnits.EQ: ("=", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.LT: ("<", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.GT: (">", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.LTE: ("[", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.GTE: ("]", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.SUBSET: ("c", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    # | logical operator | 1st subunit | 2nd subunit              | 3rd subunit              |
    # | ---------------- | ----------- | ------------------------ | ------------------------ |
    # | logical and      | `&`         | value or register (`N`)  | value or register (`N`)  |
    # | logical or       | `\|`        | value or register (`N`)  | value or register (`N`)  |
    # | logical not      | `!`         | value or register (`N`)  | value or register (`N`)  |
    # | logical xor      | `^`         | value or register (`N`)  | value or register (`N`)  |
    # | bitwise and      | `7`         | value or register (`NS`) | value or register (`NS`) |
    # | bitwise or       | `\`         | value or register (`NS`) | value or register (`NS`) |
    # | bitwise not      | `1`         | value or register (`NS`) | value or register (`NS`) |
    # | bitwise xor      | `6`         | value or register (`NS`) | value or register (`NS`) |
    TyuUnits.AND: ("&", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.OR: ("|", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.NOT: ("!", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.XOR: ("^", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.BAND: ("7", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.BOR: ("\\", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.BNOT: ("1", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.BXOR: ("6", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
}
UNIT_SYNTAX_STARTS: dict[str, TyuUnits] = {v[0]: k for k, v in UNIT_SYNTAXES.items()}


class TyuProgram(NamedTuple):
    global_functions: dict[str, str] = {}
    top_level_code: list[str] = []


def parse(program: str, debug: bool = False) -> TyuProgram:
    """parses a 3yu program"""
    return TyuProgram()


def analyse(program: TyuProgram, debug: bool = False) -> list[str]:
    """analyses for incorrect types and usages and returns a list of error messages"""
    return []
