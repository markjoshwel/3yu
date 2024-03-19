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
from sys import stderr
from typing import Any, Generator, NamedTuple


class TyuUnits(Enum):
    WHITESPACE = 0
    COMMENT = 1
    SCOPE = 2
    DECLARATION = 3
    ASSIGNMENT = 4
    INCLUDE = 5
    IF = 6
    CALL = 7
    RETURN = 8
    ADD = 9
    CONCAT = 10
    SUB = 11
    MUL = 12
    DIV = 13
    MOD = 14
    LSHIFT = 15
    RSHIFT = 16
    SUBSET = 17
    EQ = 18
    LT = 19
    GT = 20
    LTE = 21
    GTE = 22
    AND = 23
    OR = 24
    NOT = 25
    XOR = 26
    BAND = 27
    BOR = 28
    BNOT = 29
    BXOR = 30


class TyuSubUnit(Enum):
    TEXT = 0  # any text until the next unit's character as a delimiter
    REGISTER = 1  # any text until "~" OR a "#" followed by an integer
    VALUE = 2  # integer or rational number, string, list or a scope
    SCOPE = 3
    SCOPE_INNARD = 4  # any text until the next unit's character as a delimiter
    TYPE = 5  # N, I, R, C, S, L<int size><type>, F<argument type><return type>


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

    def __str__(self) -> str:
        return "*"  # TODO: implement


UNIT_SYNTAX: dict[TyuUnits, tuple[str, TyuSubUnit, str | TyuSubUnit]] = {
    # | declaration/directive | 1st subunit | 2nd subunit                       | 3rd subunit                       |
    # | --------------------- | ----------- | --------------------------------- | --------------------------------- |
    # | comment               | `;`         | comment text                      | `;` or newline                    |
    # | scope declaration     | `(`         | scope instructions                | `)`                               |
    # | register declaration  | `d`         | name (see below for restrictions) | type, see [types](#types)         |
    # | assignment            | `:`         | target register                   | incoming register, value or scope |
    # | include directive     | `#`         | file path                         | `~`                               |
    TyuUnits.COMMENT: (";", TyuSubUnit.TEXT, ";"),
    TyuUnits.SCOPE: ("(", TyuSubUnit.SCOPE_INNARD, ")"),
    TyuUnits.DECLARATION: ("d", TyuSubUnit.TEXT, TyuSubUnit.TYPE),
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
UNIT_SYNTAX_STARTS: dict[str, TyuUnits] = {v[0]: k for k, v in UNIT_SYNTAX.items()}

class TyuScope(NamedTuple):
    declarations: list["TyuUnit"] = []
    functions: list["TyuUnit"] = []
    units: list["TyuUnit"] = []


SubunitType = str | int | float | TyuScope | TyuType


class TyuUnit(NamedTuple):
    unit: TyuUnits
    subunit1: str
    subunit2: SubunitType
    subunit3: SubunitType


class TyuProgram(NamedTuple):
    global_functions: dict[str, TyuUnit] = {}
    top_level_code: list[TyuUnit] = []


class ParseError(Exception):
    column: int = 0
    line: int = 0

    def __init__(
        self,
        *args,
        column: int = 0,
        line: int = 0,
    ) -> None:
        self.column = column
        self.line = line
        super().__init__(*args)


def englishify(subunit_number: int) -> str:
    match subunit_number:
        case 2:
            return "2nd"

        case 3:
            return "3rd"

        case _:
            return f"{subunit_number}"


def debug_return_decorator(func):
    def wrapper(*args, **kwargs):
        stderr.write(f"debug: {func.__name__} called with {args=} {kwargs=}\n")
        result = func(*args, **kwargs)
        stderr.write(f"debug: {func.__name__} returned {repr(result)}\n")
        return result

    return wrapper

@debug_return_decorator
def parse_subunit(
    iterator: Generator[tuple[int, int, str, str], None, None],
    current_unit: TyuUnits,
    subunit_number: int,
    expected_subunit: TyuSubUnit | str,
) -> SubunitType:
    basket: list[str] = []

    match expected_subunit:
        case TyuSubUnit.TEXT:
            basket = []

            for line, column, char, next_char in iterator:
                if next_char == UNIT_SYNTAX[current_unit][-1]:
                    return "".join(basket).strip()

                basket.append(char)

            else:
                raise ParseError(
                    f"was expecting a {expected_subunit.name.lower()} "
                    f"{englishify(subunit_number)} subunit for "
                    f"the {current_unit.name.lower()} unit, "
                    "but reached the end of file instead",
                    line=line,
                    column=column,
                )

        case TyuSubUnit.VALUE | TyuSubUnit.REGISTER as subunit:
            # either a string literal, numeric or a register
            first_char = next(iterator, None)
            if first_char is None:
                raise ParseError(
                    "was expecting a "
                    f"{'value or a ' if subunit == TyuSubUnit.VALUE else ''}register "
                    f"{englishify(subunit_number)} subunit for "
                    f"the {current_unit.name.lower()} unit, "
                    "but reached the end of file instead (1)",
                    line=-1,
                    column=-1,
                )

            basket = []
            start_line, start_column, char, next_char = first_char
            basket.append(char)

            if (char.isdigit()) or (char == "-"):  # numeric
                if subunit == TyuSubUnit.REGISTER:
                    raise ParseError(
                        f"was expecting a register "
                        f"{englishify(subunit_number)} subunit for "
                        f"the {current_unit.name.lower()} unit, "
                        "but reached the end of file instead (2)",
                        line=start_line,
                        column=start_column,
                    )

                # if the next character is not a number or a dot, then we're done
                if (not next_char.isdigit()) and (next_char != "."):
                    # we've only consumed the one character, so its a single digit
                    return int(char)

                for line, column, char, next_char in iterator:
                    # if the next character is not a number or a dot, then we're done
                    if (not next_char.isdigit()) and (next_char != "."):
                        return (
                            int("".join(basket))
                            if "." not in basket
                            else float("".join(basket))
                        )
                    basket.append(char)

                else:
                    stderr.write(
                        "debug: reached end of file while parsing numeric, should this happen?\n"
                    )
                    return (
                        int("".join(basket))
                        if "." not in basket
                        else float("".join(basket))
                    )

            elif char in ("'", '"'):  # string literal
                if subunit == TyuSubUnit.REGISTER:
                    raise ParseError(
                        f"was expecting a register "
                        f"{englishify(subunit_number)} subunit for "
                        f"the {current_unit.name.lower()} unit, "
                        "but got a string literal instead",
                        line=start_line,
                        column=start_column,
                    )

                for line, column, char, next_char in iterator:
                    if (
                        char == basket[0]
                    ):  # use the same quote character to close the string
                        return "".join(basket)
                    else:
                        basket.append(char)

                else:
                    raise ParseError(
                        f"string was not closed with the same quote character ({basket[0]})",
                        line=start_line,
                        column=start_column,
                    )

            elif char == "$":  # special register
                for line, column, char, next_char in iterator:
                    basket.append(char)

                    if (not next_char.isdigit()) or (next_char != "!"):
                        try:
                            return int("".join(basket[1:]))

                        except ValueError:
                            raise ParseError(
                                f"could not parse special register number '{''.join(basket)}'), "
                                f"next character was {repr(next_char)}",
                                line=start_line,
                                column=start_column,
                            )

                    if char == "!":  # weirdhand for 0
                        basket.append("0")

                    elif char.isdigit():
                        basket.append(char)

                    else:
                        raise ParseError(
                            f"special register number was not a number (found '{char}')",
                            line=start_line,
                            column=start_column,
                        )

                else:
                    stderr.write(
                        "debug: reached end of file while parsing special register, should this happen?\n"
                    )
                    return int("".join(basket[1:]))

            else:  # named register
                for line, column, char, next_char in iterator:
                    if char == "~":
                        return "".join(basket)
                    else:
                        basket.append(char)

                else:
                    raise ParseError(
                        "register value was not closed with a '~' character",
                        line=start_line,
                        column=start_column,
                    )

        case TyuSubUnit.SCOPE:
            first_char = next(iterator, None)
            if first_char is None:
                raise ParseError(
                    "was expecting a scope, but reached the end of file instead",
                    line=-1,
                    column=-1,
                )

            line, column, _, _ = first_char

            if first_char != UNIT_SYNTAX[TyuUnits.SCOPE][0]:
                raise ParseError(
                    "was expecting the start of a scope ('('), "
                    f"but got something else ('{first_char}') instead",
                    column=column,
                    line=line,
                )

            return parse_scope(iterator=iterator)

        case TyuSubUnit.SCOPE_INNARD:
            assert "unreachable (attempted to parse a scope_innard subunit)"

        case TyuSubUnit.TYPE:
            # TODO: implement this womp womp
            return "*"

        case _:  # is a string delimiter
            for line, column, char, next_char in iterator:
                if (current_unit == TyuUnits.COMMENT) and (char == "\n"):
                    return expected_subunit

                if char != expected_subunit:
                    continue

                return expected_subunit

            else:
                raise ParseError(
                    f"was expecting a '{expected_subunit}' character,"
                    "but reached the end of file instead",
                    line=-1,
                    column=-1,
                )

    assert f"unreachable (did not return after parsing a subunit) - {expected_subunit}: {basket}"


def parse_scope(
    iterator: Generator[tuple[int, int, str, str], None, None],
    debug: bool = False,
) -> TyuScope:
    """
    assumes the first character has already been consumed;
    will consume the ending scope delimiter
    """

    line: int = 1
    column: int = 1
    current_unit: TyuUnits = TyuUnits.WHITESPACE
    scope: list[TyuUnit] = []

    def dprint(message: Any) -> None:
        if debug:
            stderr.write(f"debug: line {line}, column {column}\t{message}\n")

    for line, column, char, _ in iterator:
        if (current_unit == TyuUnits.WHITESPACE) and (char in UNIT_SYNTAX_STARTS):
            current_unit = UNIT_SYNTAX_STARTS[char]
            dprint(f"\t{char} -> {current_unit.name}")
            continue

        try:
            match current_unit:
                case TyuUnits.WHITESPACE:
                    continue

                case TyuUnits.SCOPE:
                    scope.append(
                        TyuUnit(
                            unit=current_unit,
                            subunit1=char,
                            subunit2=parse_scope(iterator=iterator),
                            subunit3=str(UNIT_SYNTAX[current_unit][2]),
                        )
                    )

                case TyuUnits.IF:
                    scope.append(
                        TyuUnit(
                            unit=current_unit,
                            subunit1=UNIT_SYNTAX[unit][0],
                            subunit2=parse_subunit(
                                iterator=iterator,
                                current_unit=current_unit,
                                subunit_number=2,
                                expected_subunit=UNIT_SYNTAX[current_unit][1],
                            ),
                            subunit3=parse_scope(iterator=iterator),
                        )
                    )

                case _ as unit:
                    scope.append(
                        TyuUnit(
                            unit=unit,
                            subunit1=UNIT_SYNTAX[unit][0],
                            subunit2=parse_subunit(
                                iterator=iterator,
                                current_unit=unit,
                                subunit_number=2,
                                expected_subunit=UNIT_SYNTAX[current_unit][1],
                            ),
                            subunit3=parse_subunit(
                                iterator=iterator,
                                current_unit=unit,
                                subunit_number=3,
                                expected_subunit=UNIT_SYNTAX[current_unit][2],
                            ),
                        )
                    )
            
            stderr.write(f"debug: parsed {scope[-1]}\n")

        except ParseError as err:
            stderr.write(
                f"an error occured while parsing line {err.line}, "
                f"column {err.column}: {err}\n"
            )
            exit(2)

    # TODO: figure out which units are declarations and which are functions once parsing types is implemented
    return TyuScope(
        # declarations=[u for u in scope if u.unit == TyuUnits.DECLARATION],
        # functions=[],
        units=scope
    )


def parse(source: str, debug: bool = False) -> TyuScope:
    """parses a 3yu program"""

    def iterate_program() -> Generator[tuple[int, int, str, str], None, None]:
        line: int = 1
        column: int = 1

        # pretend the program is a scope
        yield 0, 0, UNIT_SYNTAX[TyuUnits.SCOPE][0], ""
        for idx, character in enumerate(source):
            next_char = source[idx + 1] if (idx < (len(source) - 1)) else ""
            stderr.write(f"debug: \t\twe are at {line=}\t{column=}\t{character=}\t{next_char=}\n")
            yield line, column, character, next_char

            if character == "\n":
                line += 1
                column = 1
            else:
                column += 1

    program_iterator = iterate_program()
    program = parse_scope(iterator=program_iterator, debug=debug)

    return program


def analyse(program: TyuScope, debug: bool = False) -> list[str]:
    """analyses for incorrect types and usages and returns a list of error messages"""
    return []
