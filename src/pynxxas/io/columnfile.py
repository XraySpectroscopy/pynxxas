#!/usr/bin/env python
"""
  Larch column file reader: read_ascii
"""
import os
import sys
import time
import string
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .xas_beamlines import guess_beamline
from .utils import (read_textfile, fix_varname,
                    MAX_FILESIZE, COMMENTCHARS)

def colname(txt):
    return fix_varname(txt.strip().lower()).replace(".", "_")

def getfloats(txt, sepchars=(",", "|", "\t"), invalid=None):
    """convert a line of numbers into a list of floats,
    as for reading a file with columnar numerical data.

    Arguments
    ---------
      txt   (string) : line of text to parse
      sepchars (list or tuple of strings): accepted
            separators of values (in addition to " ")
            default is (",", "|", "\t")
      invalid (object): value to use for words that
            cannot be converted to float [None]
    Returns
    -------
      list with each entry either a float or None

    """
    tclean = txt.replace("\n"," ").replace("\r"," ")
    for sep in sepchars:
        tclean = tclean.replace(sep, " ")
    words = [w.strip() for w in tclean.split()]
    for i, w in enumerate(words):
        try:
            words[i] = float(w)
        except ValueError:
            words[i] = invalid
    return words


def read_columnfile(filename, labels=None, simple_labels=False,
               sort=False, sort_column=0):
    """read a plaintext column file, returning a group
    containing the data extracted from the file.

    Arguments:
      filename (str):        name of file to read
      labels (ist or None) : list of labels to use for array labels [None]
      simple_labels (bool) : whether to force simple column labels (note 1) [False]
      sort (bool) :          whether to sort row data (note 2) [False]
      sort_column (int) :    column to use for sorting (note 2) [0]

    Returns:
      namespace

      A data group containing data read from file, with several attributes:

         | filename     : text name of the file.
         | array_labels : array labels, names of 1-D arrays.
         | data         : 2-dimensional data (ncolumns, nrows) with all data.
         | header       : array of text lines of the header.
         | footer       : array of text lines of the footer (text after the numerical data)
         | attrs        : group of attributes parsed from header lines.

    Notes:
      1. array labels.  If `labels` is `None` (the default), column labels
         and names of 1d arrays will be guessed from the file header.  This often
         means parsing the final header line, but tagged column files from several XAFS
         beamlines will be tried and used if matching.  Column labels may be like 'col1',
         'col2', etc if suitable column labels cannot be guessed.
         These labels will be used as names for the 1-d arrays from each column.
         If `simple_labels` is  `True`, the names 'col1', 'col2' etc will be used
         regardless of the column labels found in the file.

      2. sorting.  Data can be sorted to be in increasing order of any column,
         by giving the column index (starting from 0).

      3. header parsing. If header lines are of the forms of

           | KEY : VAL
           | KEY = VAL

         these will be parsed into a 'attrs' dictionary in the returned group.

    Examples:

        >>> feo_data = read_column_file("feo_rt1.dat")

    """
    if not Path(filename).exists():
        raise OSError(f"File not found: '{filename}'")
    if os.stat(filename).st_size > MAX_FILESIZE:
        raise OSError(f"File '{filename}' too big for read_column_file()")

    text = read_textfile(filename)
    lines = text.split("\n")

    ncol = None
    data, footers, headers = [], [], []

    lines.reverse()
    section = "FOOTER"

    for line in lines:
        line = line.strip()
        if len(line) < 1:
            continue
        # look for section transitions (going from bottom to top)
        if section == "FOOTER" and not None in getfloats(line):
            section = "DATA"
        elif section == "DATA" and None in getfloats(line):
            section = "HEADER"

        # act of current section:
        if section == "FOOTER":
            footers.append(line)
        elif section == "HEADER":
            headers.append(line)
        elif section == "DATA":
            rowdat  = getfloats(line)
            if ncol is None:
                ncol = len(rowdat)
            elif ncol > len(rowdat):
                rowdat.extend([np.nan]*(ncol-len(rowdat)))
            elif ncol < len(rowdat):
                for i in data:
                    i.extend([np.nan]*(len(rowdat)-ncol))
                ncol = len(rowdat)
            data.append(rowdat)

    # reverse header, footer, data, convert to arrays
    footers.reverse()
    headers.reverse()
    data.reverse()
    data = np.array(data).transpose()

    # try to parse attributes from header text
    header_attrs = {}
    for hline in headers:
        hline = hline.strip().replace("\t", " ")
        if len(hline) < 1: continue
        if hline[0] in COMMENTCHARS:
            hline = hline[1:].strip()
        keywds = []
        if ":" in hline: # keywords in  "x: 22"
            words = hline.split(":", 1)
            keywds = words[0].split()
        elif "=" in hline: # keywords in  "x = 22"
            words = hline.split("=", 1)
            keywds = words[0].split()
        if len(keywds) == 1:
            key = colname(keywds[0])
            if key.startswith("_"):
                key = key[1:]
            if len(words) > 1:
                header_attrs[key] = words[1].strip()

    fpath = Path(filename)
    attrs = {"filename": filename}
    group = SimpleNamespace(name=filename, filename=fpath.name,
                           header=headers, data=[], array_labels=[])

    if len(data) == 0:
        return group

    if sort and sort_column >= 0 and sort_column < ncol:
         data = data[:, np.argsort(data[sort_column])]

    group.data = data

    if len(footers) > 0:
        group.footer = footers

    group.attrs = SimpleNamespace(name=f"header attributes from '{filename}'")
    for key, val in header_attrs.items():
        setattr(group.attrs, key, val)

    if isinstance(labels, str):
        for bchar in ",#@%|:*":
            labels = labels.replace(bchar, "")
        labels = labels.split()
    if labels is None and not simple_labels:
        bldat = guess_beamline(headers)(headers)
        labels = bldat.get_array_labels()

        if getattr(bldat, "energy_units", "eV") != "eV":
            group.energy_units = bldat.energy_units
        if getattr(bldat, "energy_column", 1) != 1:
            group.energy_column = bldat.energy_column
        if getattr(bldat, "mono_dspace", -1) > 0:
            group.mono_dspace = bldat.mono_dspace

    set_array_labels(group, labels=labels, simple_labels=simple_labels)
    return group

def set_array_labels(group, labels=None, simple_labels=False,
                     save_oldarrays=False):

    """set array names for a group from its 2D `data` array.

    Arguments
    ----------
      labels (list of strings or None)  array of labels to use
      simple_labels (bool):   flag to use ("col1", "col2", ...) [False]
      save_oldarrays (bool):  flag to save old array names [False]


    Returns
    -------
       group with newly named attributes of 1D array data, and
       an updated `array_labels` giving the mapping of `data`
       columns to attribute names.

    Notes
    ------
      1. if `simple_labels=True` it will overwrite any values in `labels`

      3. Array labels must be valid python names. If not enough labels
         are specified, or if name clashes arise, the array names may be
         modified, often by appending an underscore and letter or by using
         ("col1", "col2", ...) etc.

      4. When `save_oldarrays` is `False` (the default), arrays named in the
         current `group.array_labels` will be erased.  Other arrays and
         attributes will not be changed.

    """
    write = sys.stdout.write
    if not hasattr(group, "data"):
        write(f"cannot set array labels for group {group}: no `data`\n")
        return

    # clear old arrays, if desired
    oldlabels = getattr(group, "array_labels", None)
    if oldlabels is not None and not save_oldarrays:
        for attr in oldlabels:
            if hasattr(group, attr):
                delattr(group, attr)

    ncols, nrow = group.data.shape

    ####
    # step 1: determine user-defined labels from input options
    # generating array `tlabels` for test labels
    #
    # generate simple column labels, used as backup
    clabels = [f"col{i+1:d}" for i in range(ncols)]

    if isinstance(labels, str):
        labels = labels.split()


    tlabels = labels
    # if simple column names requested or above failed, use simple column names
    if simple_labels or tlabels is None:
        tlabels = clabels

    ####
    # step 2: check input and correct problems
    # 2.a: check for not enough and too many labels
    if len(tlabels) < ncols:
        for i in range(len(tlabels), ncols):
            tlabels.append(f"col{i+1:d}")
    elif len(tlabels) > ncols:
        tlabels = tlabels[:ncols]

    # 2.b: check for names that clash with group attributes
    # or that are repeated, append letter.
    reserved_names = ("data", "array_labels", "filename",
                      "attrs", "header", "footer")
    extras = string.ascii_lowercase
    labels = []
    for i in range(ncols):
        lname = tlabels[i]
        if lname in reserved_names or lname in labels:
            lname = lname + "_a"
            j = 0
            while lname in labels:
                j += 1
                if j == len(extras):
                    break
                lname = f"{tlabels[i]}_{extras[j]}"
        if lname in labels:
            lname = clabels[i]
        labels.append(lname)

    ####
    # step 3: assign attribue names, set "array_labels"
    for i, name in enumerate(labels):
        setattr(group, name, group.data[i])
    group.array_labels = labels
    return group


def write_ascii(filename, *args, commentchar="#", label=None, header=None):
    """
    write a list of items to an ASCII column file

    Arguments:
      args (list of groups):     list of groups to write.
      commentchar (str) :        character for comment ("#")
      label (str on None):       array label line (autogenerated)
      header (list of strings):  array of strings for header

    Returns:
      None

    Examples:
       >>> write_ascii("myfile",  group.energy, group.norm, header=["comment1", "comment2"]

    """
    ARRAY_MINLEN = 2
    write = sys.stdout.write
    com = commentchar
    label = label
    if header is None:
        header = []

    arrays = []
    arraylen = None

    for arg in args:
        if isinstance(arg, np.ndarray):
            if len(arg) > ARRAY_MINLEN:
                if arraylen is None:
                    arraylen = len(arg)
                else:
                    arraylen = min(arraylen, len(arg))
                arrays.append(arg)
            else:
                header.append(repr(arg))

        else:
            header.append(repr(arg))

    if arraylen is None:
        msg = f"write_ascii() need arrays with {ARRAY_MINLEN:d} or more elements."
        raise ValueError(msg)

    buff = []
    if header is None:
        buff = [f"{com} empty header"]
    for s in header:
        buff.append(f"{com} {s}")
    buff.append(f"{com}--------------------------------")
    if label is None:
        label = (" "*13).join([f"col{i+1:d}" for i in range(len(arrays))])
    buff.append(f"{com} {label}")

    arrays = np.array(arrays)
    for i in range(arraylen):
        w = [gformat(val[i], length=14) for val in arrays]
        buff.append(" ".join(w))
    buff.append("")

    with open(filename, "w", encoding=sys.getdefaultencoding()) as fout:
        fout.write("\n".join(buff))
    write(f"wrote to file '{filename}'")


def read_fdmnes(filename, **kwargs):
    """read [FDMNES](http://fdmnes.neel.cnrs.fr/) ascii files"""
    group = read_ascii(filename, **kwargs)
    group.header_dict = dict(filetype="FDMNES", energy_units="eV")
    for headline in group.header:
        if ("E_edge" in headline):
            if headline.startswith("#"):
                headline = headline[1:]
            vals = [float(v) for v in headline.split(" = ")[0].split(" ") if v]
            vals_names = headline.split(" = ")[1].split(", ")
            group.header_dict.update(dict(zip(vals_names, vals)))
    group.name = f"FDMNES file {filename}"
    group.energy += group.header_dict["E_edge"]
    #fix _arrlabel -> arrlabel
    for ilab, lab in enumerate(group.array_labels):
        if lab.startswith("_"):
            fixlab = lab[1:]
            group.array_labels[ilab] = fixlab
            delattr(group, lab)
            setattr(group, fixlab, group.data[ilab])
    return group

def guess_filereader(path, return_text=False):
    """guess function name to use to read a data file based on the file header

    Arguments
    ---------
    path (str) : file path to be read

    Returns
    -------
    name of function (as a string) to use to read file
    if return_text: text of the read file
    """
    text = read_textfile(path)
    lines = text.split("\n")
    line1 = lines[0].lower()
    reader = "read_ascii"
    if "epics scan" in line1:
        reader = "read_gsescan"
    if "xdi" in line1:
        reader = "read_xdi"
    if "epics stepscan file" in line1 :
        reader = "read_gsexdi"
    if ("#s" in line1) or ("#f" in line1):
        reader = "read_specfile"
    if "fdmnes" in line1:
        reader = "read_fdmnes"
    if return_text:
        return reader, text
    else:
        return reader
