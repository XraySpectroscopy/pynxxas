import io
from math import log10

from charset_normalizer import from_bytes


MAX_FILESIZE = 100 * 1024 * 1024  # 100 Mb limit
COMMENTCHARS = "#;%*!$"

VALID_CHARS1 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"

BAD_FILECHARS = ";~,`!%$@$&^?*#:\"/|'\\\t\r\n (){}[]<>"
GOOD_FILECHARS = "_" * len(BAD_FILECHARS)

BAD_VARSCHARS = BAD_FILECHARS + "=+-."
GOOD_VARSCHARS = "_" * len(BAD_VARSCHARS)

TRANS_FILE = str.maketrans(BAD_FILECHARS, GOOD_FILECHARS)
TRANS_VARS = str.maketrans(BAD_VARSCHARS, GOOD_VARSCHARS)


def fix_varname(s):
    """fix string to be a a good Python variable/attribute name."""
    t = str(s).translate(TRANS_VARS)

    if len(t) < 1:
        t = "_var_"
    if t[0] not in VALID_CHARS1:
        t = "_%s" % t
    while t.endswith("_"):
        t = t[:-1]
    return t


def read_textfile(filename, size=None):
    """read text from a file as string

    Argument
    --------
    filename  (str or file): name of file to read or file-like object
    size  (int or None): number of bytes to read

    Returns
    -------
    text of file as string.

    Notes
    ------
    1. the encoding is detected with charset_normalizer.from_bytes
       which is then used to decode bytes read from file.
    2. line endings are normalized to be '\n', so that
       splitting on '\n' will give a list of lines.
    3. if filename is given, it can be a gzip-compressed file
    """
    text = ""

    def decode(bytedata):
        return str(from_bytes(bytedata).best())

    if isinstance(filename, io.IOBase):
        text = filename.read(size)
        if filename.mode == "rb":
            text = decode(text)
    else:
        with open(filename, "rb") as fh:
            text = decode(fh.read(size))
    return text.replace("\r\n", "\n").replace("\r", "\n")


def gformat(val, length=11):
    """Format a number with '%g'-like format.

    Except that:
        a) the length of the output string will be of the requested length.
        b) positive numbers will have a leading blank.
        b) the precision will be as high as possible.
        c) trailing zeros will not be trimmed.

    The precision will typically be ``length-7``.

    Parameters
    ----------
    val : float
        Value to be formatted.
    length : int, optional
        Length of output string (default is 11).

    Returns
    -------
    str
        String of specified length.

    Notes
    ------
    Positive values will have leading blank.

    """
    if val is None or isinstance(val, bool):
        return f"{repr(val):>{length}s}"
    try:
        expon = int(log10(abs(val)))
    except (OverflowError, ValueError):
        expon = 0
    length = max(length, 7)
    form = "e"
    prec = length - 7
    ab_expon = abs(expon)
    if ab_expon > 99:
        prec -= 1
    elif (
        (expon >= 0 and expon < (prec + 4))
        or (expon <= -1 and -expon < (prec - 2))
        or (expon <= -1 and prec < 5 and abs(expon) < 3)
    ):
        form = "f"
        prec += 4
        if expon > 0:
            prec -= expon

    def fmt(val, length, prec, form):
        out = f"{val:{length}.{prec}{form}}"
        if form == "e" and "e+0" in out or "e-0" in out:
            out = f"{val:{length+1}.{prec+1}{form}}"
            out = out.replace("e-0", "e-").replace("e+0", "e+")
        return out

    prec += 1
    out = "_" * (length + 2)
    while len(out) > length:
        prec -= 1
        out = fmt(val, length, prec, form)
    if "_" in out:
        out = fmt(val, length, prec, form)
    while len(out) < length:
        prec += 1
        out = fmt(val, length, prec, form)
    return out


def test_gformat():
    for x in range(-10, 12):
        for a in [0.2124312134, 0.54364253, 0.812312, 0.96341312124, 1.028456789]:
            v = a * (10 ** (x))
            for len in (14, 13, 12, 11, 10, 9, 8):
                print(gformat(v, length=len))
