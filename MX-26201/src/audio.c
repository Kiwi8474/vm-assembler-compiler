#ifndef AUDIO_H
#define AUDIO_H

#export play_note
#export play_song

def uint16 play_note_freq;
def uint16 play_note_duration;
void play_note(play_note_freq, play_note_duration) {
    out 0x30, uint16 $play_note_freq;
    out 0x31, uint16 $play_note_duration;
    out 0x32, 0;
    return;
}

def uint16 song_player_sector_num;
def uint16 song_player_ptr;
def uint16 song_player_target;
def uint16 song_player_freq;
def uint16 song_player_duration;
void play_song(song_player_sector_num, song_player_ptr) {
    load(uint16 $song_player_sector_num, uint16 $song_player_ptr);
    uint16 song_player_target = uint16 $song_player_ptr + 512;
    while uint16 $song_player_ptr < uint16 $song_player_target {
        uint16 song_player_freq = uint16 $$song_player_ptr;

        if uint16 $song_player_freq == 0xFFFF {
            return;
        }

        uint16 song_player_ptr = uint16 $song_player_ptr + 2;

        uint16 song_player_duration = uint16 $$song_player_ptr;
        uint16 song_player_ptr = uint16 $song_player_ptr + 2;

        if uint16 $song_player_freq == 0 {
            out 0x40, uint16 $song_player_duration;
        } else {
            play_note(uint16 $song_player_freq, uint16 $song_player_duration);
        }
    }
    return;
}

#endif