import random
import string
import subprocess


def gifoeb_gen(width=500, height=500, colors=256, animate=False, tool="IM"):
    if tool.upper() not in ("IM", "GM"):
        raise ValueError("`tool` must be 'IMG' or 'GM'")

    gif = gen_dumping_gif(width, height, tool=tool.upper(), animate=animate, colors=colors)
    return gif


def gifoeb_recover(pict_data, tool="IM", colors=256):
    if tool.upper() not in ("IM", "GM"):
        raise ValueError("`tool` must be 'IMG' or 'GM'")

    palette = recover(load_picture(pict_data, tool=tool.upper()), colors=colors)
    palette_bytes = bytes(bytearray().join(map(bytearray, palette)))

    return palette_bytes


def gen_picture(w, h, colors=256):
    square_size = 1
    while True:
        if (w // square_size) * (h // square_size) < colors:
            break
        square_size *= 2

    if square_size == 1:
        raise ValueError("picture size too small")

    square_size //= 2
    per_row = w // square_size
    per_column = h // square_size

    pict = []
    for i in range(per_column):
        line = []
        for j in range(per_row):
            color = (i * per_row + j) % colors
            line.extend([color] * square_size)
        line.extend([line[-1]] * (w - len(line)))
        pict.extend([line] * square_size)
    pict.extend([pict[-1]] * (h - len(pict)))
    return pict


def gen_gif_saving_palette():
    return [(i, i, i) for i in range(256)]


def gen_random_palette():
    palette = []
    for _ in range(256):
        palette.append(tuple(random.randint(0, 255) for _ in range(3)))
    return palette


def gen_testing_text_palette():
    text = (
        """Lorem ipsum dolor sit amet, consectetur adipiscing elit,
sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut
enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi
ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit
in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur
sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt
mollit anim id est laborum."""
        * 10
    )
    palette = []
    for i in range(256):
        palette.append(tuple(map(ord, text[i * 3 : i * 3 + 3])))  # noqa E203
    return palette


def make_ppm(palette, picture):
    h = len(picture)
    assert h > 0
    w = len(picture[0])
    pict_data = bytearray("P6\n{} {}\n255\n".format(w, h).encode("utf8"))
    for r in picture:
        assert len(r) == w
        for v in r:
            pict_data.extend(palette[v])
    return bytes(pict_data)


def load_pixels(w, h, data):
    assert len(data) == w * h * 3
    pixels = []
    for i in range(h):
        row = []
        for j in range(w):
            pix = []
            for c in range(3):
                pix.append(bytearray([data[(i * w + j) * 3 + c]])[0])
            row.append(tuple(pix))
        pixels.append(row)
    return pixels


def gen_dumping_gif(w, h, tool="GM", animate=False, colors=256):
    palette_size_log = 1
    while 2**palette_size_log < colors:
        palette_size_log += 1

    palette = gen_gif_saving_palette()[: 2**palette_size_log]
    picture = gen_picture(w, h, colors=colors)
    ppm_data = make_ppm(palette, picture)
    assert tool in ("GM", "IM")
    if tool == "GM":
        prefix = ["gm"]
    else:
        prefix = []

    command = prefix + ["convert", "ppm:-"]
    command.append("gif:-")
    convert = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    if animate:
        ppm_data *= 2  # generate second image (the same as first)
    stdout, stderr = convert.communicate(ppm_data)
    assert convert.returncode == 0, "convert failed"
    palette_data = bytearray().join(map(bytearray, palette))
    gif_data = bytearray(stdout)
    assert gif_data[10] == 0xF0 | (palette_size_log - 1)
    gif_data[10] ^= 0x80
    comment = bytearray(b"!\xfe\x20")
    comment.extend(ord(random.choice(string.ascii_letters)) for _ in range(32))  # cache prevention
    comment.append(0)
    gif_data[13 : 13 + len(palette_data)] = comment  # noqa E203
    return bytes(gif_data)


def load_picture(pict_data, tool="GM", picture_index=0):
    assert tool in ("GM", "IM")
    if tool == "GM":
        prefix = ["gm"]
    else:
        prefix = []

    identify = subprocess.Popen(
        prefix + ["identify", "-format", "%w %h", "-[{}]".format(picture_index)], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    stdout, stderr = identify.communicate(pict_data)
    assert identify.returncode == 0, "identify failed"
    w, h = map(int, stdout.decode("utf8").split())
    convert = subprocess.Popen(prefix + ["convert", "-[{}]".format(picture_index), "RGB:-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = convert.communicate(pict_data)
    assert convert.returncode == 0, "convert failed"
    pixels = load_pixels(w, h, stdout)
    return pixels


def recover(pixels, colors=256):
    palette_options = [[] for _ in range(colors)]
    w = len(pixels[0])
    h = len(pixels)
    orig = gen_picture(w, h, colors)
    for x in range(h):
        for y in range(w):
            palette_options[orig[x][y]].append(pixels[x][y])

    palette = []
    for opts in palette_options:
        col = []
        if not opts:
            palette.append((None, None, None))
            continue
        cnts = {}
        for c in opts:
            cnts[c] = cnts.get(c, 0) + 1
        elected = max(cnts, key=cnts.get)
        col.extend(elected)
        palette.append(tuple(col))
    return palette


def test_recover(fmt, palette, w, h, quality=None, save_pict=None, tool="GM", colors=256):
    pict = gen_picture(w, h, colors=colors)
    ppm = make_ppm(palette, pict)
    assert tool in ("GM", "IM")
    if tool == "GM":
        prefix = ["gm"]
    else:
        prefix = []

    assert all(x in string.digits + string.ascii_letters for x in fmt), "oi vey"

    if quality is None:
        quality = []
    else:
        quality = ["-quality", str(quality)]
    convert = subprocess.Popen(prefix + ["convert", "-"] + quality + [fmt + ":-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = convert.communicate(ppm)
    assert convert.returncode == 0, "convert failed"
    pict_data = stdout
    if save_pict is not None:
        with open(save_pict, "wb") as f:
            f.write(pict_data)
    pixels = load_picture(pict_data, tool)
    recovered_palette = recover(pixels, colors=colors)

    total = errors = 0
    for i in range(colors):
        for j in range(3):
            total += 1
            if palette[i][j] != recovered_palette[i][j]:
                errors += 1

    print("test completed, {} bytes total, {} recovered wrong ({:.2f}%)".format(total, errors, errors * 100 / total))
