"""
3yu.cli: command line interface for 3yu
---------------------------------------
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

from pathlib import Path
from sys import argv, stderr, stdout

from .backend import run
from .frontend import analyse, parse
from . import __doc__ as doc


def entry():
    match argv:
        case [prog, _path, *args]:
            path = Path(_path)
            if not (path.exists() and path.is_file()):
                stderr.write(f"error: '{path}' dpes not exist\n")
                exit(1)

            debug = False
            if "-d" in args or "--debug" in args:
                debug = True

            tyu_program = parse(path.read_text(encoding="utf-8"), debug=debug)

            if "-a" in args or "--ast" in args:
                stdout.write(f"{tyu_program}\n")
                exit(0)

            for error in analyse(tyu_program, debug=debug):
                stderr.write(error)
                exit(2)

            run(tyu_program, debug=debug)

        case _:
            stderr.write(
                f"{doc.splitlines()[1].split(':', maxsplit=1)[-1].strip()}\n"
                "\n"
                "usage:\n"
                f"   {argv[0]} <path to 3yu source file> [flags]\n"
                "\n"
                "flags:\n"
                "   -d, --debug\tprint debug information\n"
                "   -a, --ast  \tprint the abstract syntax tree; will not run the program\n"
            )
