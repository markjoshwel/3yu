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

register : "#"  NUMBER+  ";"
         | UNICODE+ "~"
         ;

value       : val_integer | val_float | val_string ;
val_integer : NUMBER+ ;
val_float   : NUMBER+  "."  NUMBER+ ;
val_string  : "\""  UNICODE+  "\"" ;

type            : type_primitives | "E" ;
type_primitives : ( "N" | "I" | "R" | "C" | "S" ) ;
type_list       : "L"  ( NUMBER+ | "_" )  type ;
type_function   : "F"  type               type ;

control : if | else | call | return ;
if      : "?"  ( register | value | scope )        decl_scope ;
else    : ","  ( register | value | scope | "_" )  decl_scope ;
call    : "@"  ( register | name | "!" )           ( register | "_" ) ;
return  : "`"  register  "`" ;

declaration   : decl_scope | decl_register ;
decl_scope    : "("  unit*     ")"  ;
decl_register : "d"  name      type ;

assignment : ":"  register  ( register | value | decl_scope ) ;
include    : "#"  UNICODE+  "~" ;
comment    : ";"  UNICODE+  "~" ;

mathematical : ( "+" | "-" | "*" | "/" | "%" | "l" | "r" )
               ( register | value )
               ( register | value ) ;
relational   : ( "=" | "<" | ">" | "[" | "]" | "c" )
               ( register | value )
               ( register | value )
             | "t"
               ( register | value )
               type ;
logical      : ( "&" | "|" | "!" | "^" | "7" | "\\" | "1" | "6" )
               ( register | value )
               ( register | value ) ;
```
