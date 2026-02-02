#org 0x200
#sectors 1

#define userspace 0x400

load 1, userspace;
goto userspace;