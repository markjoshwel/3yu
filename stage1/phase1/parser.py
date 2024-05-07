"""
3yu stage1 interpreter: frontend phase1a - parser
-------------------------------------------------
with all my heart, mark <mark@joshwel.co>, 2024

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
from typing import Literal, NamedTuple


# syntax-related data structures


class TyuUnitEnum(Enum):
    # unit    : comment
    #         | assignment
    #         | include
    #         | control
    #         | declaration
    #         | expression
    #         ;
    WHITESPACE = 1
    COMMENT = 2
    ASSIGNMENT = 3
    INCLUDE = 4
    CONTROL = 5
    CONTROL_IF = 6
    CONTROL_ELSE = 7
    CONTROL_CALL = 8
    CONTROL_RETURN = 9
    DECLARATION = 10
    DECLARATION_SCOPE = 11
    DECLARATION_REGISTER = 12
    EXPRESSION = 13

    def __repr__(self) -> str:  # reimpl not needed
        return f"{self.__class__.__name__}.{self.name}"


class TyuSubunitEnum(Enum):
    NUMBER = 1
    CHARACTER = 2
    VALUE = 3
    REGISTER = 4
    NAME = 5
    SCOPE_INNARD = 6
    TYPE = 7

    def __repr__(self) -> str:  # reimpl not needed
        return f"{self.__class__.__name__}.{self.name}"


class OneOrMore(NamedTuple):
    unit: TyuUnitEnum | TyuSubunitEnum

    def __repr__(self) -> str:  # reimpl not needed
        return f"{self.unit}+"


class ZeroOrMore(NamedTuple):
    unit: TyuUnitEnum | TyuSubunitEnum

    def __repr__(self) -> str:  # reimpl not needed
        return f"{self.unit}*"


TyuSubUnitPrimitiveType = TyuUnitEnum | TyuSubunitEnum | OneOrMore | ZeroOrMore | str
TyuSubunitType = TyuSubUnitPrimitiveType | list[TyuSubUnitPrimitiveType]

TyuSyntax: dict[TyuUnitEnum, tuple[TyuSubunitType, ...]] = {
    # control : if | else | call | return ;
    # if      : "?"  ( register | value | decl_scope )        decl_scope ;
    # else    : ","  ( register | value | decl_scope | "_" )  decl_scope ;
    # call    : "@"  ( register | decl_scope | "!" )          ( register | "_" ) ;
    # return  : "`"  ( register | value | decl_scope )        "`" ;
    TyuUnitEnum.CONTROL: (
        [
            TyuUnitEnum.CONTROL_IF,
            TyuUnitEnum.CONTROL_ELSE,
            TyuUnitEnum.CONTROL_CALL,
            TyuUnitEnum.CONTROL_RETURN,
        ],
    ),
    TyuUnitEnum.CONTROL_IF: (
        "?",
        [TyuSubunitEnum.REGISTER, TyuSubunitEnum.VALUE, TyuUnitEnum.DECLARATION_SCOPE],
        TyuUnitEnum.DECLARATION_SCOPE,
    ),
    TyuUnitEnum.CONTROL_ELSE: (
        "?",
        [
            TyuSubunitEnum.REGISTER,
            TyuSubunitEnum.VALUE,
            TyuUnitEnum.DECLARATION_SCOPE,
            "_",
        ],
        TyuUnitEnum.DECLARATION_SCOPE,
    ),
    TyuUnitEnum.CONTROL_CALL: (
        "@",
        [
            TyuSubunitEnum.REGISTER,
            TyuUnitEnum.DECLARATION_SCOPE,
            "!",
        ],
        TyuUnitEnum.DECLARATION_SCOPE,
    ),
    TyuUnitEnum.CONTROL_RETURN: (
        "`",
        [TyuSubunitEnum.REGISTER, TyuSubunitEnum.VALUE, TyuUnitEnum.DECLARATION_SCOPE],
        "`",
    ),
    # declaration   : decl_scope | decl_register ;
    # decl_scope    : "("  unit*     ")"  ;
    # decl_register : "d"  name      type ;
    TyuUnitEnum.DECLARATION: (
        [TyuUnitEnum.DECLARATION_SCOPE, TyuUnitEnum.DECLARATION_REGISTER],
    ),
    TyuUnitEnum.DECLARATION_SCOPE: ("(", TyuSubunitEnum.SCOPE_INNARD, ")"),
    TyuUnitEnum.DECLARATION_REGISTER: (
        "d",
        TyuSubunitEnum.NAME,
        TyuSubunitEnum.TYPE,
    ),
    # assignment : ":"  register  ( register | value | decl_scope ) ;
    # include    : "#"  CHARACTER+  "~" ;
    # comment    : ";"  CHARACTER*  ( "\n" | ";") ;
    TyuUnitEnum.ASSIGNMENT: (
        ":",
        TyuSubunitEnum.REGISTER,
        [
            TyuSubunitEnum.REGISTER,
            TyuSubunitEnum.VALUE,
            TyuUnitEnum.DECLARATION_SCOPE,
        ],
    ),
    TyuUnitEnum.INCLUDE: (
        "#",
        OneOrMore(TyuSubunitEnum.CHARACTER),
    ),
    TyuUnitEnum.COMMENT: (
        ";",
        ZeroOrMore(TyuSubunitEnum.CHARACTER),
        ["\n", ";"],
    ),
    # expression : ( "+" | "-" | "*" | "/" | "%" | "l" | "r"
    # .              | "=" | "<" | ">" | "[" | "]" | "c"
    # .              | "&" | "|" | "!" | "^" | "7" | "\\" | "1" | "6" )
    # .            ( register | value )
    # .            ( register | value );
    TyuUnitEnum.EXPRESSION: (
        [
            "+",
            "-",
            "*",
            "/",
            "%",
            "l",
            "r",
            "=",
            "<",
            ">",
            "[",
            "]",
            "c",
            "&",
            "|",
            "!",
            "^",
            "7",
            "\\",
            "1",
            "6",
            "t",
        ],
        [TyuSubunitEnum.REGISTER, TyuSubunitEnum.VALUE],
        [TyuSubunitEnum.REGISTER, TyuSubunitEnum.VALUE],
    ),
}


# abstract syntax tree / ast-related data structures


class TyuBasicType(NamedTuple):
    type: Literal["N"] | Literal["I"] | Literal["R"] | Literal["C"] | Literal["S"]


class TyuListType(NamedTuple):
    length: int
    contenttype: TyuBasicType | "TyuListType" | "TyuFunctionType"
    type: str = "L"


class TyuFunctionType(NamedTuple):
    argtype: TyuBasicType | TyuListType | "TyuFunctionType"
    rettype: TyuBasicType | TyuListType | "TyuFunctionType"
    type: str = "F"


TyuType = TyuBasicType | TyuListType | TyuBasicType


class TyuNamedRegister(NamedTuple):
    name: str
    type: TyuType


class TyuSpecialRegister(NamedTuple):
    number: int
    type: TyuType


TyuRegister = TyuNamedRegister | TyuSpecialRegister


class TyuRational(NamedTuple):
    numerator: int
    denominator: int


class TyuScope(NamedTuple):
    units: list["TyuUnit"]


class TyuUnit(NamedTuple):
    sub1: TyuUnitEnum
    sub2: str | int | TyuRational | TyuScope | TyuType | TyuRegister
    sub3: str | int | TyuRational | TyuScope | TyuType | TyuRegister


def parse(source: str) -> TyuScope:
    return TyuScope([])
