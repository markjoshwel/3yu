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
    ISTYPE = 31

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


class TyuSubUnit(Enum):
    TEXT = 0  # any text until the next unit's character as a delimiter
    REGISTER = 1  # any text until "~" OR a "#" followed by an integer
    REGISTER_NAME = 2  # any text until "~"; used in declarations
    VALUE = 3  # integer or rational number, string, list or a scope
    SCOPE = 4
    SCOPE_INNARD = 5  # any text until the next unit's character as a delimiter
    TYPE = 6  # N, I, R, C, S, L<int size><type>, F<argument type><return type>, E


class TyuTypes(Enum):
    NUMERIC = "N"
    INTEGER = "I"
    RATIONAL = "R"
    CONTAINER = "C"
    STRING = "S"
    LIST = "L"
    ELEMENT = "E"
    FUNCTION = "F"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


class TyuTypesPart(Enum):
    TYPE_SINGLE = 0
    TYPE_MULTIPLE = 1
    SIZE = 2


class TyuSingleType(NamedTuple):
    type: TyuTypes


class TyuListType(NamedTuple):
    size: int
    types: tuple["TyuType", ...] = ()
    type: TyuTypes = TyuTypes.LIST

class TyuFunctionType(NamedTuple):
    argument: "TyuType"
    return_type: "TyuType"
    type: TyuTypes = TyuTypes.FUNCTION


TyuType = TyuSingleType | TyuListType | TyuFunctionType


class TyuCompileTimeType(NamedTuple):
    type: TyuListType | TyuSingleType
    value: str


TYPE_SYNTAX: dict[
    TyuTypes,
    tuple[str] | tuple[str, TyuTypesPart, TyuTypesPart],
] = {
    # - `N`: number
    #   - `I`: integer
    #   - `R`: rational
    # - `C`: container
    #   - `S`: string
    #   - `L<size><type(s)>`: list
    # - `E`: element
    # - `F<argument type><return type>`: function
    TyuTypes.NUMERIC: ("N",),
    TyuTypes.INTEGER: ("I",),
    TyuTypes.RATIONAL: ("R",),
    TyuTypes.CONTAINER: ("C",),
    TyuTypes.STRING: ("S",),
    TyuTypes.LIST: ("L", TyuTypesPart.SIZE, TyuTypesPart.TYPE_MULTIPLE),
    TyuTypes.FUNCTION: ("F", TyuTypesPart.TYPE_SINGLE, TyuTypesPart.TYPE_SINGLE),
    TyuTypes.ELEMENT: ("E",),
}
TYPE_SYNTAX_STARTS: dict[str, TyuTypes] = {v[0]: k for k, v in TYPE_SYNTAX.items()}


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
    TyuUnits.DECLARATION: ("d", TyuSubUnit.REGISTER_NAME, TyuSubUnit.TYPE),
    TyuUnits.ASSIGNMENT: (":", TyuSubUnit.REGISTER, TyuSubUnit.VALUE),
    TyuUnits.INCLUDE: ("#", TyuSubUnit.TEXT, "~"),
    # | control instruction | 1st subunit | 2nd subunit                       | 3rd subunit                        |
    # | ------------------- | ----------- | --------------------------------- | ---------------------------------- |
    # | if                  | `?`         | register, value or scope          | scope                              |
    # | function call       | `@`         | function or register name, or `!` | register for argument, `_` if none |
    # | return              | `` ` ``     | register                          | `` ` ``                            |
    TyuUnits.IF: ("?", TyuSubUnit.VALUE, TyuSubUnit.SCOPE),
    TyuUnits.CALL: ("@", TyuSubUnit.REGISTER, TyuSubUnit.VALUE),
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
    # | is type                 | `t`         | value or register        | type                     |
    TyuUnits.EQ: ("=", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.LT: ("<", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.GT: (">", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.LTE: ("[", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.GTE: ("]", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.SUBSET: ("c", TyuSubUnit.VALUE, TyuSubUnit.VALUE),
    TyuUnits.ISTYPE: ("t", TyuSubUnit.VALUE, TyuSubUnit.TYPE),
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
    declarations: tuple["TyuUnit", ...] = ()
    units: tuple["TyuUnit", ...] = ()


class TyuRegister(NamedTuple):
    name: int | str  # ints for special registers, strings for named registers


SubunitType = str | int | float | TyuScope | TyuType | TyuCompileTimeType | TyuRegister


class TyuUnit(NamedTuple):
    type: TyuUnits
    subunit1: str
    subunit2: SubunitType
    subunit3: SubunitType


class ParseError(Exception):
    line: int = 0
    column: int = 0

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
    match int(str(subunit_number)[-1]):
        case 1:
            return f"{subunit_number}st"

        case 2:
            return f"{subunit_number}nd"

        case 3:
            return f"{subunit_number}rd"

        case _:
            return f"{subunit_number}th"


ProgramIterator = Generator[tuple[int, int, str, str], None, None]


def _parse_subunit_text(
    iterator: ProgramIterator,
    current_unit: TyuUnits,
    subunit_number: int,
    debug: bool = False,
) -> str:
    basket: list[str] = []

    for line, column, char, next_char in iterator:
        basket.append(char)

        if next_char == UNIT_SYNTAX[current_unit][-1]:
            return "".join(basket).strip()

        if (current_unit != TyuUnits.COMMENT) and (
            char == UNIT_SYNTAX[TyuUnits.COMMENT][0]
        ):
            raise ParseError(
                f"was expecting a text {englishify(subunit_number)} subunit for "
                f"the {current_unit.name.lower()} unit, "
                "but was stopped by a comment",
                line=line,
                column=column,
            )

        if current_unit == (TyuUnits.COMMENT) and (next_char == "\n"):
            return "".join(basket).strip()

    else:
        if current_unit == TyuUnits.COMMENT:
            return "".join(basket).strip()

        raise ParseError(
            f"was expecting a text {englishify(subunit_number)} subunit for "
            f"the {current_unit.name.lower()} unit, "
            "but reached the end of file instead",
            line=line,
            column=column,
        )


def _parse_subunit_value(
    iterator: ProgramIterator,
    current_unit: TyuUnits,
    subunit_number: int,
    expected_subunit: TyuSubUnit,
    debug: bool = False,
) -> str | int | float | TyuRegister | TyuScope:
    basket: list[str] = []
    subunit = expected_subunit

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

    start_line, start_column, char, next_char = first_char
    basket = [char]

    # advance to a non-whitespace character
    while char.isspace():
        start_line, start_column, char, next_char = next(iterator)
        basket = [char]

    if char == UNIT_SYNTAX[TyuUnits.COMMENT][0]:
        raise ParseError(
            f"was expecting a {expected_subunit.name.lower()} "
            f"{englishify(subunit_number)} subunit for "
            f"the {current_unit.name.lower()} unit, "
            "but was stopped by a comment",
            line=start_line,
            column=start_column,
        )

    elif char == UNIT_SYNTAX[TyuUnits.SCOPE][0]:
        return parse_scope(iterator=iterator, debug=debug)

    elif (char.isdigit()) or (char == "-"):  # numeric
        if subunit in [TyuSubUnit.REGISTER, TyuSubUnit.REGISTER_NAME]:
            raise ParseError(
                f"was expecting a register{'name' if subunit == TyuSubUnit.REGISTER_NAME else ''} "
                f"{englishify(subunit_number)} subunit for "
                f"the {current_unit.name.lower()} unit, "
                "but reached the end of file instead (2)",
                line=start_line,
                column=start_column,
            )

        if char == "-" and not next_char.isdigit():
            raise ParseError(
                f"negated value does not precede a number digit",
                line=start_line,
                column=start_column,
            )

        # if the next character is not a number or a dot, then we're done
        if (not next_char.isdigit()) and (next_char != "."):
            # we've only consumed the one character, so its a single digit
            try:
                return int(char)

            except ValueError:
                raise ParseError(
                    f"could not parse numeric subunit of value '{char}' "
                    f"for the {current_unit.name.lower()} unit",
                    line=start_line,
                    column=start_column,
                )

        for line, column, char, next_char in iterator:
            basket.append(char)

            # if the next character is not a number or a dot, then we're done
            if (not next_char.isdigit()) and (next_char != "."):
                try:
                    return (
                        int("".join(basket))
                        if "." not in basket
                        else float("".join(basket))
                    )

                except ValueError:
                    raise ParseError(
                        f"could not parse numeric subunit of value '{''.join(basket)}' "
                        f"for the {current_unit.name.lower()} unit",
                        line=start_line,
                        column=start_column,
                    )

        else:
            stderr.write(
                "debug: reached end of file while parsing numeric, should this happen?\n"
            )
            try:
                return (
                    int("".join(basket)) if "." not in basket else float("".join(basket))
                )

            except ValueError:
                raise ParseError(
                    f"could not parse numeric subunit of value '{''.join(basket)}' "
                    f"for the {current_unit.name.lower()} unit",
                    line=start_line,
                    column=start_column,
                )

    elif char in ("'", '"'):  # string literal
        if subunit in [TyuSubUnit.REGISTER, TyuSubUnit.REGISTER_NAME]:
            raise ParseError(
                f"was expecting a register{'name' if subunit == TyuSubUnit.REGISTER_NAME else ''} "
                f"{englishify(subunit_number)} subunit for "
                f"the {current_unit.name.lower()} unit, "
                "but got a string literal instead",
                line=start_line,
                column=start_column,
            )

        for line, column, char, next_char in iterator:
            if char == basket[0]:  # use the same quote character to close the string
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
                    return TyuRegister(name=int("".join(basket[1:])))

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
                return TyuRegister("".join(basket))
            else:
                basket.append(char)

        else:
            raise ParseError(
                "register value was not closed with a '~' character",
                line=start_line,
                column=start_column,
            )


# TODO: complex types that cannot be determine at parse time (e.g. list of unknown length)
#       are currently unsupported
#       the idea here will be to return a special type that can be resolved at a later time
#
#       for this, _parse_subunit_type should be changed to read the whole type based on the
#       rule of types being a single word only having either uppercase characters, numbers
#       or underscores
#
#       if the type has an underscore in it, then we just return the TyuCompileTimeType
#       with the type (either a func or a list) and the value being the whole type string
#
#       else, we give it to _parse_type which should now be its own function that takes
#       a string and returns a TyuType, rather than operating on a ProgramIterator


def _parse_subunit_type(
    iterator: ProgramIterator,
    current_unit: TyuUnits,
    subunit_number: int,
    expected_subunit: TyuSubUnit,
    debug: bool = False,
) -> TyuType:
    # return TyuSingleType(type=TyuTypes.NUMERIC)

    def _parse_type(
        first_char: str,
        iterator: ProgramIterator,
        line: int,
        column: int,
        max_n: int = 0,
    ) -> tuple[TyuType, ...]:
        if first_char not in TYPE_SYNTAX_STARTS:
            raise ParseError(
                "was firstly expecting an uppercase type character, "
                f"but got '{first_char}' instead",
                line=line,
                column=column,
            )

        def _iterator_overrider() -> ProgramIterator:
            yield line, column, first_char, ""
            for i, t in enumerate(iterator, start=1):
                yield t

        new_iterator = _iterator_overrider()
        type_basket: list[TyuType] = []

        for line, column, char, next_char in new_iterator:
            match char:
                case TyuTypes.LIST.value:
                    if debug:
                        stderr.write(
                            f"debug: line {line}, column {column}: "
                            f"parsing {repr(char)} ({TYPE_SYNTAX_STARTS[first_char]})\n"
                        )
                    
                    size_basket: list[str] = []
                    list_size: int | None = None

                    for line, column, char, next_char in iterator:
                        size_basket.append(char)

                        if not char.isdigit():
                            if char == "_":
                                list_size = (
                                    -1
                                )  # special size used for unknown length lists (_)
                                break

                            else:
                                raise ParseError(
                                    f"was expecting a list size number, "
                                    f"but got '{char}' instead",
                                    line=line,
                                    column=column,
                                )

                        if not next_char.isdigit() and list_size is None:
                            list_size = int("".join(size_basket))
                            break

                    else:
                        raise ParseError(
                            f"was expecting a list size number, "
                            "but reached the end of file instead",
                            line=line,
                            column=column,
                        )

                    next_iteration = next(new_iterator, None)
                    if next_iteration is None:
                        raise ParseError(
                            "was expecting a list size number, "
                            "but reached the end of file instead",
                            line=-1,
                            column=-1,
                        )
                    
                    if debug:
                        stderr.write(
                            f"debug: line {line}, column {column}: "
                            "recursing for list inner type\n"
                        )

                    type_basket.append(
                        TyuListType(
                            size=list_size,
                            types=_parse_type(
                                first_char=next_iteration[2],
                                iterator=iterator,
                                line=next_iteration[0],
                                column=next_iteration[1],
                            ),
                        ),
                    )

                case TyuTypes.FUNCTION.value:
                    if debug:
                        stderr.write(
                            f"debug: line {line}, column {column}: "
                            f"parsing {repr(char)} ({TYPE_SYNTAX_STARTS[first_char]})\n"
                        )

                    next_iteration = next(new_iterator, None)
                    if next_iteration is None:
                        raise ParseError(
                            "was expecting an argument type for the function type, "
                            "but reached the end of file instead",
                            line=-1,
                            column=-1,
                        )
                    
                    if debug:
                        stderr.write(
                            f"debug: line {line}, column {column}: "
                            "recursing for argument type\n"
                        )
                    
                    argument = _parse_type(
                        first_char=next_iteration[2],
                        iterator=iterator,
                        line=next_iteration[0],
                        column=next_iteration[1],
                        max_n=1,
                    )[0]

                    next_iteration = next(new_iterator, None)
                    if next_iteration is None:
                        raise ParseError(
                            "was expecting a return type for the function type, "
                            "but reached the end of file instead",
                            line=-1,
                            column=-1,
                        )
                    
                    if debug:
                        stderr.write(
                            f"debug: line {line}, column {column}: "
                            "recursing for return type\n"
                        )
                    
                    return_type = _parse_type(
                        first_char=next_iteration[2],
                        iterator=iterator,
                        line=next_iteration[0],
                        column=next_iteration[1],
                        max_n=1,
                    )[0]

                    type_basket.append(
                        TyuFunctionType(
                            argument=argument,
                            return_type=return_type,
                        ),
                    )

                case _ as possible_type:
                    if possible_type not in TYPE_SYNTAX_STARTS:
                        raise ParseError(
                            f"was expecting an uppercase type character, "
                            f"but got '{possible_type}' instead",
                            line=line,
                            column=column,
                        )

                    if debug:
                        stderr.write(
                            f"debug: line {line}, column {column}: "
                            f"parsing {repr(char)} ({TYPE_SYNTAX_STARTS[first_char]})\n"
                        )

                    type_basket.append(
                        TyuSingleType(type=TYPE_SYNTAX_STARTS[first_char]),
                    )

            if (max_n >= 1) and (len(type_basket) >= max_n):
                return tuple(type_basket)

        else:
            raise ParseError(
                f"was expecting a type character, " "but reached the end of file instead",
                line=-1,
                column=-1,
            )

    for line, column, char, next_char in iterator:
        if char == UNIT_SYNTAX[TyuUnits.COMMENT][0]:
            raise ParseError(
                f"was expecting a {expected_subunit.name.lower()} "
                f"{englishify(subunit_number)} subunit for "
                f"the {current_unit.name.lower()} unit, "
                "but was stopped by a comment",
                line=line,
                column=column,
            )

        # skip whitespace
        if char.isspace():
            continue

        # we've hit a character
        if char not in TYPE_SYNTAX_STARTS:
            raise ParseError(
                f"was expecting an uppercase type character, but got '{char}' instead",
                line=line,
                column=column,
            )

        else:
            return _parse_type(
                first_char=char,
                iterator=iterator,
                line=line,
                column=column,
                max_n=1,
            )[0]

    else:
        raise ParseError(
            f"was expecting a {expected_subunit.name.lower()} "
            f"{englishify(subunit_number)} subunit for "
            f"the {current_unit.name.lower()} unit, "
            "but reached the end of file instead",
            line=-1,
            column=-1,
        )


def _parse_subunit(
    iterator: ProgramIterator,
    current_unit: TyuUnits,
    subunit_number: int,
    expected_subunit: TyuSubUnit | str,
    debug: bool = False,
) -> SubunitType:
    match expected_subunit:
        case TyuSubUnit.TEXT:
            return _parse_subunit_text(
                iterator=iterator,
                current_unit=current_unit,
                subunit_number=subunit_number,
                debug=debug,
            )

        case TyuSubUnit.VALUE | TyuSubUnit.REGISTER | TyuSubUnit.REGISTER_NAME as subunit:
            # either a string literal, numeric or a register
            return _parse_subunit_value(
                iterator=iterator,
                current_unit=current_unit,
                subunit_number=subunit_number,
                expected_subunit=expected_subunit,
                debug=debug,
            )

        case TyuSubUnit.SCOPE:
            return _parse_scope_subunit(
                iterator=iterator,
                current_unit=current_unit,
                subunit_number=subunit_number,
                expected_subunit=expected_subunit,
                debug=debug,
            )

        case TyuSubUnit.SCOPE_INNARD:
            assert False, "unreachable (attempted to parse a scope_innard subunit)"

        case TyuSubUnit.TYPE:
            return _parse_subunit_type(
                iterator=iterator,
                current_unit=current_unit,
                subunit_number=subunit_number,
                expected_subunit=expected_subunit,
                debug=debug,
            )

        case _:  # is a string delimiter
            basket: list[str] = []

            for line, column, char, next_char in iterator:
                if (current_unit != TyuUnits.COMMENT) and (
                    char == UNIT_SYNTAX[TyuUnits.COMMENT][0]
                ):
                    raise ParseError(
                        f"was expecting {repr(expected_subunit)} "
                        f"{englishify(subunit_number)} subunit for "
                        f"the {current_unit.name.lower()} unit, "
                        "but was stopped by a comment",
                        line=line,
                        column=column,
                    )

                if char == expected_subunit:
                    return expected_subunit

                elif (current_unit == TyuUnits.COMMENT) and (char == "\n"):
                    return char

            else:
                if current_unit == TyuUnits.COMMENT:
                    return "\n"

                raise ParseError(
                    f"was expecting a '{expected_subunit}' character, "
                    "but reached the end of file instead",
                    line=-1,
                    column=-1,
                )


def _parse_scope_subunit(
    iterator: ProgramIterator,
    current_unit: TyuUnits,
    subunit_number: int,
    expected_subunit: TyuSubUnit,
    debug: bool = False,
) -> TyuScope:

    first_char = next(iterator, None)
    if first_char is None:
        raise ParseError(
            "was expecting a scope, but reached the end of file instead",
            line=-1,
            column=-1,
        )

    start_line, start_column, char, next_char = first_char
    basket = [char]

    # advance to a non-whitespace character
    while char.isspace():
        start_line, start_column, char, next_char = next(iterator)
        basket = [char]

    if char == UNIT_SYNTAX[TyuUnits.COMMENT][0]:
        raise ParseError(
            f"was expecting a {expected_subunit.name.lower()} "
            f"{englishify(subunit_number)} subunit for "
            f"the {current_unit.name.lower()} unit, "
            "but was stopped by a comment",
            line=start_line,
            column=start_column,
        )

    elif char == UNIT_SYNTAX[TyuUnits.SCOPE][0]:
        return parse_scope(iterator=iterator, debug=debug)

    else:
        raise ParseError(
            "was expecting the start of a scope ('('), "
            f"but got something else ('{first_char}') instead",
            line=start_line,
            column=start_column,
        )


def parse_scope(
    iterator: ProgramIterator,
    debug: bool = False,
) -> TyuScope:
    """
    assumes the first character has already been consumed;
    will consume the ending scope delimiter
    """

    line: int = 0
    column: int = 0
    current_unit: TyuUnits = TyuUnits.WHITESPACE
    scope: list[TyuUnit] = []

    def dprint(message: Any) -> None:
        if debug:
            stderr.write(f"debug: line {line}, column {column}: {message}\n")

    # part 1: lexical analysis

    for line, column, char, _ in iterator:
        if (current_unit == TyuUnits.WHITESPACE) and (char in UNIT_SYNTAX_STARTS):
            current_unit = UNIT_SYNTAX_STARTS[char]
            dprint(f"matched char {char} as {current_unit.name}")

        if char == UNIT_SYNTAX[TyuUnits.SCOPE][2]:
            break

        try:
            match current_unit:
                case TyuUnits.WHITESPACE as unit:
                    # dprint(f"matched unit as {unit}")
                    continue

                case TyuUnits.SCOPE as unit:
                    dprint(f"matched unit as {unit} - {UNIT_SYNTAX[unit]}")
                    scope.append(
                        TyuUnit(
                            type=unit,
                            subunit1=char,
                            subunit2=parse_scope(iterator=iterator, debug=debug),
                            subunit3=str(UNIT_SYNTAX[unit][2]),
                        )
                    )
                    current_unit = TyuUnits.WHITESPACE

                case TyuUnits.IF as unit:
                    dprint(f"matched unit as {unit} - {UNIT_SYNTAX[unit]}")
                    expected_subunit3 = UNIT_SYNTAX[unit][2]
                    assert isinstance(expected_subunit3, TyuSubUnit)
                    scope.append(
                        TyuUnit(
                            type=unit,
                            subunit1=UNIT_SYNTAX[unit][0],
                            subunit2=_parse_subunit(
                                iterator=iterator,
                                current_unit=unit,
                                subunit_number=2,
                                expected_subunit=UNIT_SYNTAX[unit][1],
                                debug=debug,
                            ),
                            subunit3=_parse_scope_subunit(
                                iterator=iterator,
                                current_unit=unit,
                                subunit_number=3,
                                expected_subunit=expected_subunit3,
                                debug=debug,
                            ),
                        )
                    )
                    current_unit = TyuUnits.WHITESPACE

                case _ as unit:
                    dprint(f"matched unit as {unit}")
                    dprint(f"parsing subunit 2 ({UNIT_SYNTAX[unit][1]})")
                    subunit2 = _parse_subunit(
                        iterator=iterator,
                        current_unit=unit,
                        subunit_number=2,
                        expected_subunit=UNIT_SYNTAX[unit][1],
                        debug=debug,
                    )
                    dprint(f"parsing subunit 3 ({UNIT_SYNTAX[unit][2]})")
                    subunit3 = _parse_subunit(
                        iterator=iterator,
                        current_unit=unit,
                        subunit_number=3,
                        expected_subunit=UNIT_SYNTAX[unit][2],
                        debug=debug,
                    )
                    scope.append(
                        TyuUnit(
                            type=unit,
                            subunit1=UNIT_SYNTAX[unit][0],
                            subunit2=subunit2,
                            subunit3=subunit3,
                        )
                    )
                    current_unit = TyuUnits.WHITESPACE

            dprint(f"finished parsing unit {scope[-1].type}")

        except ParseError as err:
            stderr.write(
                f"an error occured while parsing line {err.line}, "
                f"column {err.column}: {err}\n"
            )
            exit(2)

    # part 2: auto curry any functions

    return TyuScope(
        declarations=(),
        units=tuple(scope),
    )


def parse(source: str, debug: bool = False) -> TyuScope:
    """parses a 3yu program"""

    def iterate_program() -> ProgramIterator:
        line: int = 1
        column: int = 1

        # pretend the program is a scope
        yield 1, 0, UNIT_SYNTAX[TyuUnits.SCOPE][0], ""
        for idx, character in enumerate(source):
            next_char = source[idx + 1] if (idx < (len(source) - 1)) else ""
            # if debug:
            #     stderr.write(f"\tat {line=}\t{column=}\t{character=}\t{next_char=}\n")
            yield line, column, character, next_char

            if character == "\n":
                line += 1
                column = 1
            else:
                column += 1

    program_iterator = iterate_program()
    next(
        program_iterator
    )  # parse_scope assumes the first character has already been consumed
    program = parse_scope(iterator=program_iterator, debug=debug)

    return program


def analyse(program: TyuScope, debug: bool = False) -> tuple[str, ...]:
    """analyses for incorrect types and usages and returns a list of error messages"""
    # TODO: semantic analysis
    stderr.write("error: analysis not implemented yet\n")
    return ()
