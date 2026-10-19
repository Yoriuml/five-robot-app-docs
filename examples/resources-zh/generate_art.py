"""Create original stroke art for the Chinese greeting, with no font dependency."""
from pathlib import Path
import struct

def generate():
    pixels = [0x0841] * (240*240)
    # Original geometric strokes spelling 你好. This is art, not a general font.
    strokes = [(50,68,56,83),(44,83,50,90),(50,83,56,132),
               (72,68,78,80),(65,79,97,85),(91,84,97,99),
               (77,84,83,127),(68,124,81,130),(62,103,68,120),(89,103,95,120),
               (119,69,125,96),(113,94,137,100),(131,83,137,113),
               (118,107,143,113),(138,99,144,107),(116,121,136,127),
               (152,72,180,78),(174,77,180,88),(161,87,167,97),
               (150,97,183,103),(161,103,167,127),(151,124,166,130)]
    for x0,y0,x1,y1 in strokes:
        for y in range(y0,y1):
            for x in range(x0,x1): pixels[y*240+x]=0xffe0
    out=Path(__file__).parent/'resources/hello.rgb565'
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(struct.pack('<57600H', *pixels))

if __name__=='__main__': generate()
