.org 0x400

movi r15, k_main

loop_start:
    movi r0, 0
    movi r1, 0
    movi r15, loop

loop:
    movi r15, loop

; Erwartet VGA Adresse in r0, Zeichen in r1
print_char:
    poke r1, r0
    pop r15

k_main:
    movi r0, 0x87CF
    movi r1, 0x41
    movi r5, 126

    movi r2, loop_start
    push r2

    movi r15, print_char

continue:
    movi r3, 1
    add r1, r3
    add r0, r3
    movi r4, push_addr
    jne r1, r5, r4
    movi r4, call_func
    je r1, r5, r4
push_addr:
    push r2
    movi r15, call_func
call_func:
    movi r15, print_char