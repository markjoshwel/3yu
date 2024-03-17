# 3yu

a horrible esoteric language where everything is 3 segments wide

oh and its almost-pure functional too i guess

roadmap:

- [ ] **stage 1**: the beginning of the end  
       python parser + python (mypyc) runtime

- [ ] **stage 2**: oh thank god its 'readable'  
       the data processing counter-language, a frontend transpiler for 3yu

- [ ] **stage 3**: executables at the speed of zig  
       python parser + zig runtime

- [ ] **stage 4**: oh god why is it self-"compiled"  
       3yu parser + 3yu runtime

if i ever hit stage 3, the project has gone too far and will not be worked on thereafter

- [the nitty gritty](#the-nitty-gritty)
  - [instructions and operators](#instructions-and-operators)
    - [declarations, directives and assignment](#declarations-directives-and-assignment)
    - [control](#control)
    - [mathematical operators](#mathematical-operators)
    - [relational operators](#relational-operators)
    - [logical operators](#logical-operators)
  - [types](#types)
  - [built-in functions](#built-in-functions)
  - [functions](#functions)

## the nitty gritty

3yu is basically syntax sugar bytecode for a register-ish machine,  
register-ish because each register can be of arbitrary type and size

argv is given to the program as [type `L_S`](#types) in the [special register `$1`](#special-registers)

### instructions and operators

#### declarations, directives and assignment

| instruction          | 1st unit | 2nd unit                          | third unit                |
| -------------------- | -------- | --------------------------------- | ------------------------- |
| comment              | `\`      | comment text                      | `\` or newline            |
| scope declaration    | `(`      | scope instructions                | `)`                       |
| function declaration | `f`      | name (see below for restrictions) | scope or boxed scope      |
| register declaration | `r`      | name (see below for restrictions) | type, see [types](#types) |
| assignment           | `:`      | target register                   | incoming register         |
| include directive    | `#`      | file path                         | `~`                       |

functions are basically just named scopes, can be called recursively,
and are lazily evaluated

during register and function declaration, the name given to the instructions' second unit must be
distinguishable from special registers, and as such, must not start with `$`  
3yu also completely disregards whitespace, so an ending terminator for the name, a tilde `~`, is required

when using functions and registers, this qualified name (`<insert name here>~`) will be used

when declaring registers, a default value will be assigned to the register. see [types](#types)  
the only exception to the default assignment is when the declaration is used for arguments, where
the actual value will be assigned when the function is called

_all_ scopes can return a value, which will be stored in the [special return register `$0`](#special-registers),
if nothing was returned, `$0` will be set to 0

at the end of a scope, any registers declared in the scope will be deallocated without exception  
(except for the special return register `$0`)

the include directive basically inserts the file at the _top of the program_,
_no matter where the directive is located in the file_

#### control

| control instruction | 1st unit | 2nd unit                              | third unit                         |
| ------------------- | -------- | ------------------------------------- | ---------------------------------- |
| if                  | `?`      | register, greater than 0 to run scope | scope                              |
| function call       | `@`      | function or register name, or `!`     | register for argument, `_` if none |
| return              | `` ` ``  | register                              | `` ` ``                            |

function calls with the 2nd unit as `!` is a shorthand for `@ $0`, to make currying a little less painful

#### mathematical operators

| mathematical operator   | 1st unit | 2nd unit             | third unit            | sets `$0` to...       |
| ----------------------- | -------- | -------------------- | --------------------- | --------------------- |
| addition                | `+`      | left register (`NC`) | right register (`NE`) | the result            |
| concatenation           | `,`      | left register (`IC`) | right register (`IC`) | the result            |
| subtraction             | `-`      | left register (`N`)  | right register (`N`)  | the result            |
| multiplication          | `*`      | left register (`NC`) | right register (`NI`) | the result            |
| division                | `/`      | left register (`N`)  | right register (`N`)  | the result            |
| modulo                  | `%`      | left register (`N`)  | right register (`N`)  | the result            |
| bitshift left           | `l`      | left register (`NS`) | right register (`II`) | the result            |
| bitshift right          | `r`      | left register (`NS`) | right register (`II`) | the result            |
| proper subset/inclusion | `c`      | left register (`EE`) | right register (`CC`) | `1` if true, else `0` |

- example on reading the types:

  for addition, the left register can be one of the types `NSL` and the right register `NSE`
  and should be interpreted as the following:

  - left hand `N` (numeric) can only be used with a right hand `N` numeric
  - left hand `C` (container) can only be used with a right hand `E` element

for the `E` type, see [types](#types)

#### relational operators

| relational operator | 1st unit | 2nd unit | third unit | sets `$0` to...       |
| ------------------- | -------- | -------- | ---------- | --------------------- |
| equals              | `=`      | register | register   | `1` if true, else `0` |
| less than           | `<`      | register | register   | `1` if true, else `0` |
| greater than        | `>`      | register | register   | `1` if true, else `0` |
| less than or equal  | `[`      | register | register   | `1` if true, else `0` |
| greater than or eq  | `]`      | register | register   | `1` if true, else `0` |

#### logical operators

| logical operator | 1st unit | 2nd unit      | third unit     | sets `$0` to...       |
| ---------------- | -------- | ------------- | -------------- | --------------------- |
| and              | `&`      | left register | right register | `1` if true, else `0` |
| or               | `\|`     | left register | right register | `1` if true, else `0` |
| not              | `!`      | left register | right register | `1` if true, else `0` |
| xor              | `^`      | left register | right register | `1` if true, else `0` |
| bitwise and      | `7`      | left register | right register | `1` if true, else `0` |
| bitwise or       | `\`      | left register | right register | `1` if true, else `0` |
| bitwise not      | `1`      | left register | right register | `1` if true, else `0` |
| bitwise xor      | `6`      | left register | right register | `1` if true, else `0` |

these operators are only available for integer, rational, and string types

if for whatever reason you need a mnemonic for the bitwise logical operators,
just dont press shift

### types

three are five primitive types in 3yu:

- `N`: number

  - `I`: integer  
    defaults to `0`

  - `R`: rational  
    defaults to `0.0`

- `C`: container

  - `S`: string  
    a utf-8 unicode string  
    defaults to an empty string `""`

  - `L<size><type(s)>`: list  
    homogeneous list of a fixed size
    defaults to an empty list `[]`

    examples:

    - `L3I`: list of 3 integers
    - `L_IR`: list of unknown size where each value is either an integer or rational

- `F<argument type><return type>`: function

  defaults to a function that returns nothing

  examples:

  - `F_I`  
    function with no argument that returns an integer

  - `FSL3S`  
    function that takes a string and returns a list of 3 strings

  - `FIFIFII`  
    `(int) -> (int) -> (int) -> int` (readable version)  
    function that takes 3 integers (curried) and returns an integer

a non primitive type but used in documentation is the `E` or element type, where:

- `E` is `S` in the case of a string and is a single utf-8 character
- `E` is of type `<T>` in a list of type `L_<T>`

### special registers

these registers are used for function interop and retrieving return values

- `$0`: return value for scopes, functions, and operators, set to a `L_S` (list of strings)
  containing program arguments on program start

- `$1`, `$2`, `$3`, ...: argument registers for functions

### built-in functions

| function name | return type | argument(s)     | description                                              |
| ------------- | ----------- | --------------- | -------------------------------------------------------- |
| `stdout~`     | -           | any             | prints whatever is passed to stdout, fails silently      |
| `stderr~`     | -           | any             | prints whatever is passed to stderr, fails silently      |
| `stdin~`      | `S`         | none            | reads a line from stdin, returns empty string if nothing |
| `len~`        | `I`         | `C`             | returns the length of a string or list, 0s for integers  |
| `min~`        | `N`         | `L_N`           | returns the minimum value in a list of numbers           |
| `max~`        | `N`         | `L_N`           | returns the maximum value in a list of numbers           |
| `slice~`      | `L_E`       | `C` `I` `I` `I` | container, start, stop=`-1`, step=`1`, returns slice     |
| `index~`      | `E`         | `C` `I`         | container, index                                         |
| `range~`      | `L_N`       | `I` `I` `I`     | start, stop=`-1`, step=`1`, returns a list               |
| `take~`       | `L_E`       | `C` `I`         | takes the first n number of ekements, defaults to `1`    |
| `drop~`       | `L_E`       | `C` `I`         | drops the first n number of elements, defaults to `1`    |
| `foldl~`      | any         | `FEFEE` `E` `C` | function, initial accumulator value, list                |
| `foldr~`      | any         | `FEFEE` `E` `C` | function, initial accumulator value, list                |
| `map~`        | `L_E`       | `FE*` `C` `L`   | function, list                                           |
| `filter~`     | `L_E`       | `FEI` `C` `L`   | function, list                                           |
| `cast~`       | any         | any             | casts a value to another type, see cast matrix below     |

| target type | castable types | note                            |
| ----------- | -------------- | ------------------------------- |
| `F`         | ?              |                                 |
| `N`         | `N`            | e.g., `I` to `R` and vice versa |
| `N`         | `S`            | stringifies the number          |
| `L`         | `S`            | stringifies the list            |
| `S`         | `I`            | turns into utf-8 binary         |

if you forgot about currying, `FEFEE` means a function that takes two arguments of type
`E`, and returns a value of type `E`

for the `E` type, see [types](#types)

### functions

3yu is functional, so arguments are passed by currying

```3yu
\ declare function and then assign a scope to it
r add3~ FIFIFII
f add3~ (
   \ declare arguments by declaring registers and then
   \ assigning them to argument registers to be used

   r a~ I   : a~ $1
   r b~ I   : b~ $2
   r c~ I   : c~ $3

   \ everything up to now is basically equivalent to
   \ `function add_three (a: int, b: int, c:int)`

   + a  b
   + $0 c
   ` $0 `
)

\ because of currying, you call the function like this
@ add3~ 1
@ !     2
@ !     3
@ stdout~ $0  \ prints 6
```

other than special registers `#1-...`, functions cannot access registers outside of their scope

you can also minify it, for god knows whatever reason

```3yu
radd3~FIFIFIIfadd3~(:$1I:$2I:$3I+$1~$2~+$0c`$0`)@add3~1@!2@!3@stdout~$0
```

## examples

### fibonacci

```3yu
\ fib~ :: Function(Integer) -> Integer
r fib~ FII
f fib~ (
   \ argument declaration
   r n~ I   : n~ $1

   \ base case
   = n~ 0           \ n~ = n~ == 0
   ? n~ ( ` 0 ` )   \ if n~ is not 0, return 0

   = n~ 1           \ n~ = n~ == 1
   ? n~ ( ` 1 ` )   \ if n~ is not 1, return 1

   \ recursive case
   r left~ I
   - n~    1
   @ fib~  $0
   : left~ $0

   r right~ I
   - n~     2
   @ fib~   $0
   : right~ $0

   + left~ right~
   ` $0 `
)
```

```python
def fib(n: int) -> int:
    if n == 0:
        return 0

    if n == 1:
        return 1

    left = fib(n - 1)
    right = fib(n - 2)
    return left + right
```

### summation of a list

```3yu
\ sum~ :: Function(List[Numeric]) -> Integer
r sum~ FL_NE
f sum~ (
   \ argument declaration
   r nums~ L_N   : nums $1

   \ base case
   @ len~ nums~        \ $0 = len~(nums~)
   = $0   0            \ $0 = $0 == 0
   ? $0   ( ` 0 ` )    \ if $0 is not 0, return 0

   \ recursive case
   r head~  N          \ head~ = nums~[0]
   @ index~ nums~
   @ !      0
   : head~  $0

   @ slice~ nums~      \ $0 = nums~[1:]
   @ !      1

   @ sum~  $0          \ $0 = sum($0)
   + head~ $0          \ $0 = head~ + sum($0)
   ` $0 `              \ return $0
)
```

```python
def sum(nums: list[int | float]) -> int:
    if len(a) > 0:
        return 0

    return nums[0] + sum(nums[1:])
```
