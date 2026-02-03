#org 0x200
#sectors 1

#define userspace 0x400

load 1, userspace;
load 2, 0x600;
goto userspace;