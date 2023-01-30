import ctypes,sys
# 取自 https://www.twblogs.net/a/5b7a94642b7177392c965cff
STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12

# 字體顏色定義，由2位十六進制組成，分別取0~f，前一位指的是背景色，後一位指的是字體色
# 可以前景色與背景色組合，也可以幾種顏色通過或運算組合，組合後還是在這16種顏色中

# Windows CMD命令行 字體顏色定義 text colors
FRG_BLACK = 0x00 # black.
FRG_DARKBLUE = 0x01 # dark blue.
FRG_DARKGREEN = 0x02 # dark green.
FRG_DARKSKYBLUE = 0x03 # dark skyblue.
FRG_DARKRED = 0x04 # dark red.
FRG_DARKPINK = 0x05 # dark pink.
FRG_DARKYELLOW = 0x06 # dark yellow.
FRG_DARKWHITE = 0x07 # dark white.
FRG_DARKGRAY = 0x08 # dark gray.
FRG_BLUE = 0x09 # blue.
FRG_GREEN = 0x0a # green.
FRG_SKYBLUE = 0x0b # skyblue.
FRG_RED = 0x0c # red.
FRG_PINK = 0x0d # pink.
FRG_YELLOW = 0x0e # yellow.
FRG_WHITE = 0x0f # white.

# Windows CMD命令行 背景顏色定義 background colors
BKG_BLUE = 0x10 # dark blue.
BKG_GREEN = 0x20 # dark green.
BKG_DARKSKYBLUE = 0x30 # dark skyblue.
BKG_DARKRED = 0x40 # dark red.
BKG_DARKPINK = 0x50 # dark pink.
BKG_DARKYELLOW = 0x60 # dark yellow.
BKG_DARKWHITE = 0x70 # dark white.
BKG_DARKGRAY = 0x80 # dark gray.
BKG_BLUE = 0x90 # blue.
BKG_GREEN = 0xa0 # green.
BKG_SKYBLUE = 0xb0 # skyblue.
BKG_RED = 0xc0 # red.
BKG_PINK = 0xd0 # pink.
BKG_YELLOW = 0xe0 # yellow.
BKG_WHITE = 0xf0 # white.

# get handle
std_out_handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

def resetColor(handle=std_out_handle): #reset white
    white = FRG_RED | FRG_GREEN | FRG_BLUE
    ctypes.windll.kernel32.SetConsoleTextAttribute(handle, white)

def colorprint(mess, color, handle=std_out_handle): # 套顏色輸出，末尾無\n
    '''
    傳入color:
    color = FRG_DARKBLUE -> 只設定文字深藍
    color = BKG_DARKBLUE -> 只設定背景深藍
    color = FRG_RED | BKG_GREEN -> 綠底紅字(合成運算)
    '''
    ctypes.windll.kernel32.SetConsoleTextAttribute(handle, color)
    sys.stdout.write(mess)
    resetColor()