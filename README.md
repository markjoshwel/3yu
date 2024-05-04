# 3yu (and the Data Processing Counter-language)

a horrible, almost pure-functional esoteric language \
made with execution units that are three subunits long

```tyu
@ stdout~ ( "Hello, world!" )
```

there are two internal phases when running or compiling 3yu code:

- **phase1**: analysis

  - lexical analysis  
    (into an abstract syntax tree)

  - semantic analysis  
    (type checking and argument validation)

- **phase2**: interpretation or synthesis

  - **phase2a**  
    tree-walking interpreter

  - **phase2b**  
    zig codegen (only in the stage2 compiler)

## an equally horrible roadmap

- [ ] **stage1** ~~compiler~~ interpreter  
       “the start of the end”

      ```text
      $ python stage1/3yu.py examples/sum.3yu
      6
      ```

  - phase1 and phase2a interpreter
    written in python

- [ ] [the **data processing counter-language**](#the-data-processing-counter-language)  
       “thank god it's readable”

      ```text
      $ python dpc/dpc.py examples/sum.dpc > sum.3yu
      $ python stage1/3yu.py sum.3yu
      6
      ```

  - [ ] transpiler written in python

  - [ ] transpiler rewritten in dpc

- [ ] **stage2** compiler  
       “why is it self-compiled”

      ```text
      $ cat examples/sum.3yu > 3yu
      6
      $ cat examples/sum.dpc > 3yu --compile > 3yu.zig && zig build-exe 3yu.zig
      $ ./sum
      6
      ```

  - phase1 and phase2a interpreter + phase 2b compiler
    written in [dpc](#the-data-processing-counter-language)  
    compiled with the dpc stage2 compiler via the python stage1 interpreter

## the data processing counter-language

an alternative frontend to 3yu

firstly written in python before being rewritten in dpc

```dpc
sum: func[nums: list[_ numeric]] -> numeric = (
   if (len(nums) == 0) (return 0)
   nums[0] + sum(nums[1:])
)

stdout(sum([1, 2, 3]))
```

will be translated into the following 3yu code with `3yu -t`:

```tyu
d sum~ FL_NN ; sum.dpc:1:1 ;
: sum~ (
   ?
   (
    @ len~ nums~ ; sum.dpc:2:25 ;
    = $0 0
   )
   (
    `0` ; sum.dpc: ;
   )
   + ; sum.dpc:3:3 ;
   (
      @ index~ nums~ ; sum.dpc:3:3 ;
      @ ! 0
   )
   (
      @ slice~ nums~ ; sum.dpc:3:18 ;
      @ ! 1
      @ sum~ $0
   )
)
@ stdout~ (@sum~( ; sum.dpc:6:1 ;
   d _sum_6_12~ L3N ; sum.dpc:6:12 ;
   + _sum_6_12~ 1
   + $0 2
   + $0 3
))
```
