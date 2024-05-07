= 3yu

a horrible, almost pure-functional esoteric language \
made with execution units that are three subunits long

== Grammar

```ppg
program : unit* ;
unit    : control
        | declaration
        | assignment
        | include
        | comment
        | mathematical
        | relational
        | logical
        ;

register : "$"  NUMBER+  "$"
         | CHARACTER+ "~"
         ;

type            : type_primitives | "E" ;
type_primitives : ( "N" | "I" | "R" | "C" | "S" ) ;
type_list       : "L"  ( NUMBER+ | "_" )  type ;
type_function   : "F"  type               type ;

value       : val_integer | val_float | val_string | type ;
val_integer : NUMBER+ ;
val_float   : NUMBER+  "."  NUMBER+ ;
val_string  : "\""  CHARACTER+  "\"" ;

control : if | else | call | return ;
if      : "?"  ( register | value | decl_scope )        decl_scope ;
else    : ","  ( register | value | decl_scope | "_" )  decl_scope ;
call    : "@"  ( register | decl_scope | "!" )          ( register | "_" ) ;
return  : "`"  ( register | value | decl_scope )        "`" ;

declaration   : decl_scope | decl_register ;
decl_scope    : "("  unit*     ")"  ;
decl_register : "d"  CHARACTER+  type ;

assignment : ":"  register  ( register | value | decl_scope ) ;
include    : "#"  CHARACTER+  "~" ;
comment    : ";"  CHARACTER*  ( "\n" | ";" ) ;

expression : ( "+" | "-" | "*" | "/" | "%" | "l" | "r"
               | "=" | "<" | ">" | "[" | "]" | "c" 
               | "&" | "|" | "!" | "^" | "7" | "\\" | "1" | "6" )
             ( register | value )
             ( register | value );
```

== Built-in Functions

- mathematical
  - `abs`
  - `ceil`
  - `cos`
  - `exp`
  - `exp2`
  - `floor`
  - `log`
  - `log10`
  - `log2`
  - `max`
  - `min`
  - `round`
  - `sin`
  - `tan`
  - `trunc`
- input/output
  - `stderr`
  - `stdin`
  - `stdout`
  - `read`
  - `write`
- others
  - `as`
