#org 0x2000
#sector 10
#sectors 4

#define KEY_IO 0xFFFF

def uint8 buffer = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9};
def uint8 index;
uint8 index = uint8 buffer[6];
out 0x2, uint8 $index;

def uint8 input_buffer = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}; 
def uint16 input_index;
def uint16 temp_char;
def uint16 cmd_match;
def uint16 cmd_found;
def uint8 empty_string;
def uint16 temp_calc;

void print_header() {
    print("================================== MX-OS V1.0 ==================================");
    uint16 $text_cursor = 0x8050;
    return;
}

void check_key_and_type() {
    if uint8 $KEY_IO != 0 {
        uint8 temp_char = uint8 $KEY_IO;

        if uint8 $temp_char == 8 {
            if uint16 $text_cursor != 0x8000 {
                if uint16 $input_index > 0 {
                    uint16 input_index = uint16 $input_index - 1;
                }
                uint16 text_cursor = uint16 $text_cursor - 1;
                uint8 $text_cursor = 32;
            }
            goto end_of_check;
        }

        if uint8 $temp_char == 13 {
            uint8 $(input_buffer + uint16 $input_index) = 0;

            uint16 temp_calc = uint16 $text_cursor - 0x8000;
            while uint16 $temp_calc > 79 {
                uint16 temp_calc = uint16 $temp_calc - 80;
            }

            uint16 text_cursor = uint16 $text_cursor - uint16 $temp_calc + 80;

            if uint16 $text_cursor > 0x87CF { scroll(); }

            if uint16 $input_index > 0 {
                uint16 cmd_found = 0;

                uint16 cmd_match = strcmp(input_buffer, "metallica");
                print(empty_string);
                if uint16 $cmd_match == 0 {
                    print("Master of Puppets!");
                    uint16 cmd_found = 1;
                }

                uint16 cmd_match = strcmp(input_buffer, "james");
                print(empty_string);
                if uint16 $cmd_match == 0 {
                    print("YEAH YEAH!!");
                    uint16 cmd_found = 1;
                }

                uint16 cmd_match = strcmp(input_buffer, "cls");
                print(empty_string);
                if uint16 $cmd_match == 0 {
                    cls();
                    print_header();
                    uint16 cmd_found = 1;
                    goto skip_prompt_newline;
                }

                uint16 cmd_match = strcmp(input_buffer, "cat");
                print(empty_string);
                if uint16 $cmd_match == 0 {
                    draw_asset(0xB000, 0x8344, 7, 3);
                    uint16 cmd_found = 1;
                }

                uint16 cmd_match = strcmp(input_buffer, "guitar");
                print(empty_string);
                if uint16 $cmd_match == 0 {
                    draw_asset(0xB015, 0x82A5, 7, 8);
                    uint16 cmd_found = 1;
                }

                uint16 cmd_match = strcmp(input_buffer, "song");
                print(empty_string);
                if uint16 $cmd_match == 0 {
                    play_song(15, 0xB200);
                    uint16 cmd_found = 1;
                }

                if uint16 $cmd_found == 0 {
                    print("command not found.");
                }

                uint16 temp_calc = uint16 $text_cursor - 0x8000;
                while uint16 $temp_calc > 79 {
                    uint16 temp_calc = uint16 $temp_calc - 80;
                }
                uint16 text_cursor = uint16 $text_cursor - uint16 $temp_calc + 80;

                if uint16 $text_cursor > 0x87CF { scroll(); }

                skip_prompt_newline:
                uint16 input_index = 0;
                print("> ");
                goto end_of_check;
            }
        }

        uint8 $text_cursor = uint8 $KEY_IO;
        uint16 text_cursor = uint16 $text_cursor + 1;

        if uint16 $input_index < 15 {
            uint8 $(input_buffer + uint16 $input_index) = uint8 $temp_char;
            uint16 input_index = uint16 $input_index + 1;
        }

        if uint16 $text_cursor > 0x87CF {
            scroll();
        }

        end_of_check:
        uint8 KEY_IO = 0;
    }
    return;
}

cls();

load(14, 0xB000);

print_header();
print("> ");
def uint16 running = 1;
while uint16 $running == 1 {
    check_key_and_type();
}

print("\n!!! KERNEL PANIC !!!\n!!! KILLED KERNEL !!!\n");


while 1 == 1 {}