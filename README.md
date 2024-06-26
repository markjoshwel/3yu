# 3yu (and the Data Processing Counter-language)

a horrible, almost pure-functional esoteric language \
made with execution units that are three subunits long

```tyu
@ stdout~ (
   d message~ S
   : message~ "don't be sad. the time is coming."
   + message~ "\nand then we'll rest."
)
```

there are two internal phases when running or compiling 3yu code:

- **phase1**: analysis

  - parsing  
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

  - phase1 frontend and phase2a interpreter backend
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
    # building the stage2 compiler
    
    # transpile the stage2 compiler into 3yu
    python dpc/dpc.py stage2/3yu.dpc > 3yu.3yu
    
    # self-compile the stage2 compiler into zig using the stage1 interpreter
    cat 3yu.3yu > python stage1/3yu.py 3yu.3yu --compile > 3yu.zig
    
    # compile the generated zig code into an executable
    zig build-exe 3yu.zig
    ```

    ```text
    $ cat examples/sum.3yu > ./3yu
    6
    $ cat examples/sum.dpc > ./3yu --compile > 3yu.zig && zig build-exe 3yu.zig
    $ ./sum
    6
    ```

  - phase1 3yu + dpc frontend and phase2 interpreter + compiler backend
    written in [dpc](#the-data-processing-counter-language)

## the data processing counter-language

an alternative frontend to 3yu

firstly written in python before being rewritten in dpc

```dpc
sum: func[nums: List[_ Numeric]] -> Numeric = (
   if (len(nums) == 0) (return 0)
   nums[0] + sum(nums[1:])
)

stdout(sum([1, 2, 3]))
```

will be translated into the following 3yu code with `3yu -t`:

```tyu
d sum~ FL_NN ; sum.dpc:1:1 ;
: sum~ (
   : nums~ $1$
   ? ( ; sum.dpc:2:7 ;
      @ len~ nums~ ; sum.dpc:2:8 ;
      = $0$ 0
   ) ( ; sum.dpc:2: ;
      ` 0 ` ; sum.dpc:2:25 ;
   )
   + ( ; sum.dpc:3:4 ;
      @ index~ nums~ ; sum.dpc:3:8 ;
      @ ! 0
   ) ( ; sum.dpc:3:14 ;
      @ slice~ nums~ ; sum.dpc:3:22 ;
      @ ! 1
      @ ! ( @ len~ nums~ )
      @ ! 1
      @ sum~ $0$
   )
)

@ stdout~ ( ; sum.dpc:6:7 ;
   @ sum~ ( ; sum.dpc:6:8 ;
      d _sum_6_12~ L3I ; sum.dpc:6:12 ;
      + _sum_6_12~ 1
      + $0$ 2
      + $0$ 3
   )
)
```
