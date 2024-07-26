from  nexusformat import nexus
from pathlib import Path
import h5py
import json
import numpy as np
from larch.xafs import pre_edge
from larch.io import read_xdi, read_ascii, write_ascii
from larch.utils import gformat


PLANCK_HC = 12398.419843320027
DEG2RAD = 0.017453292519943295

def kekpf2nexus(filename, nxroot, entry_name='entry',   metadata=None):

    dat = read_ascii(filename, labels='angle_drive, angle_read, time, i0, ifluor')

    meta = {}
    if metadata is not None:
        for kf, vf in metadata.items():
            if kf not in meta:
                meta[kf.lower()] = {}
            for  k, v in vf.items():
                meta[kf.lower()][k.lower()] = v

    print(meta)
    monod = meta['monochromator']['d_spacing']

    dat.energy = PLANCK_HC/(2*monod*np.sin(DEG2RAD*(dat.data[0, : ])))
    dat.mu = dat.ifluor / dat.i0
    ncolumns = len(dat.array_labels) + 3

    pre_edge(dat, pre1=-150, pre2=-50, norm1=150, norm2=750)
    pre_offset = dat.pre_edge_details.pre_offset
    pre_slope = dat.pre_edge_details.pre_slope
    nvict = dat.pre_edge_details.nvict

    coldata = []
    coldata.append(dat.energy)
    coldata.append(dat.norm*1.0)
    coldata.append(dat.ifluor*1.0)
    coldata.append(dat.i0*1.0)

    array_labels = ['energy', 'intensity', 'ifluor', 'i0']
    ndat, npts = dat.data.shape
    for i in range(ndat):
        label = dat.array_labels[i].lower()
        if label not in array_labels:
            array_labels.append(label)
            coldata.append(dat.data[i, :])

    root = nxroot[entry_name] = nexus.NXentry()
    root.attrs['default'] = 'plot'
    root['definition'] = 'NXxas'
    root['mode'] = 'fluorescence'
    root['element'] = meta['element']['symbol']
    root['absorption_edge'] = meta['element']['edge']
    root['energy']  = dat.energy
    root['energy'].attrs['units'] = 'eV'
    root['intensity']  = dat.norm

    plot = root['plot'] = nexus.NXdata()
    plot['energy'] = root['energy']
    plot['intensity'] = root['intensity']
    plot.attrs['signal'] = 'intensity'
    plot.attrs['axes'] = 'energy'
    plot['energy'].attrs['units'] = 'eV'
    plot['energy'].attrs['long_name'] = 'Energy (eV)'
    plot['intensity'].attrs['long_name'] = 'Normalized mu(E)'

    names = {}

    #  sample
    sample = root['sample'] = nexus.NXsample()
    for aname, value in meta['sample'].items():
        setattr(sample, aname, value)
        if aname.lower() == 'name':
            names['sample'] = value
    sample['prep'] = 'unknown sample'


    #  process
    kwargs = []
    for k, v in dat.callargs.pre_edge.items():
        if v is not None:
            kwargs.append(f"{k}={v}")

    kwargs = ", ".join(kwargs)

    preline = f"pre_edge = {gformat(pre_offset, 12)} + {gformat(pre_slope, 12)}*energy"
    if nvict != 0:
        preline = f"({preline})*energy(-{dat.nvict})"

    proc = ["processing done with xraylarch version 0.9.80",
            f"larch.xafs.pre_edge(data, {kwargs})",
            "energy = col1    # column 1: energy (eV)",
            "ifluor = col3    # column 3: fluorescence intensity",
            "i0     = col4    # column 4: incident beam intensity",
            "mu  = iflour/i0  ",
             f"edge_step = {gformat(dat.edge_step, 12)}",
             preline,
            "intensity = norm = (mu - pre_edge) /edge_step"]

    notes='\n'.join(proc)

    header = ['XDI/1.1',
             'Column.1: energy eV', 'Column.2: norm']
    collabel = ['energy          ', 'norm            ']
    for i, label in enumerate(array_labels[2:]):
        header.append(f'Column.{i+3}: {label}')
        collabel.append(label +  ' '*(1+max(1, 15-len(label))))

    collabel = ' '.join(collabel)

    end_header = []
    target = header
    for j in dat.header[4:]:
        if j.startswith('#'): j = j[1:].strip()
        if '---' in j:
            break
        if '///' in j:
            target = end_header
        if j.startswith('Mono.'):
            j = j.replace('Mono.', 'Monochromator.')
        if 'Monochromator.dspa' in j:
            j = j.replace('dspacing', 'd_spacing')

        if not j.startswith('Column.'):
            target.append(j)

    header.append('Process.program: xraylarch')
    header.append('Process.version: 0.9.80')
    header.append(f'Process.command: pre_edge(data, {kwargs})')
    for i, p in enumerate(proc[2:]):
        header.append(f"Process.step{i+1:d}: {p}")
    for j in end_header:
        if j.startswith('#'):
            j = j[1:].strip()
        header.append(j)

    root['process'] = nexus.NXprocess(program='xraylarch', version='0.9.80',
                                      notes=notes)

    # rawdata
    root['rawdata'] = np.array(coldata).T
    root['rawdata'].attrs['array_labels'] = json.dumps(array_labels)

    root['reference'] = 'None'

    # scan
    scan = root['scan'] = nexus.NXcollection()
    scan.headers = json.dumps(meta)
    scan.data_collector = 'KEK PF BL9A'
    scan.filename = filename

    if 'scan' in meta:
        for key, val in meta['scan'].items():
            setattr(scan, key, val)
        if getattr(dat, 'comments', None) is not None:
            scan.comments =  dat.comments


    inst = root['instrument'] = nexus.NXinstrument()

    source = inst['source'] = nexus.NXsource(type='Synchrotron X-ray Source',
                                        probe='x-ray')

    if 'facility' in meta:
        for aname, value in meta['facility'].items():
            if aname.lower() == 'energy':
                words = value.split(maxsplit=1)
                en_value = float(words[0])
                source.energy = en_value
                if len(words) > 1:
                    source.energy.attrs['units'] = words[1]
            else:
                setattr(source, aname, value)
                if aname.lower() == 'name':
                    names['facility'] = value

    if 'beamline' in meta:
        bl = inst['beamline'] = nexus.NXcollection()
        for aname, value in meta['beamline'].items():
            setattr(bl, aname, value)
            if aname.lower() == 'name':
                names['beamline'] = value


    title_words = [names.get('sample', filename),
                   names.get('facility', ''),
                   names.get('beamline', '')]
    root['title'] = (' '.join(title_words)).strip()


    # mono
    mono_meta = meta.get('monochromator', meta.get('mono', {}))
    d_spacing = mono_meta.get('d_spacing', 3.13551)
    mono_name = mono_meta.get('name', 'Si 111')

    def parse_mono_string(mono_name):
        mono_type = 'Si'
        for k in ('()[]'):
            mono_name = mono_name.replace(k, ' ')
        for k in ('SiC', 'Si', 'Ge', 'C'):
            mono_name = mono_name.replace(k, f'{k} ')

        words = mono_name.split(maxsplit=1)
        if words[0] in ('SiC', 'Si', 'Ge', 'C'):
            mono_type = words[0]

        try:
            refl = words[1]
            if len(refl) > 3:
                refl = refl.replace(' ', ',').split(',')
            else:
                refl = (refl[0], refl[1], refl[2])

            refl = [int(w.strip()) for w in refl]
        except:
            refl = (1, 1, 1)
        return mono_type, refl

    mono_type, refl = parse_mono_string(mono_name)
    mono_crystal = nexus.NXcrystal(type=mono_type,
                                  reflection=np.array(refl),
                                  d_spacing=d_spacing)

    inst['monochromator'] = nexus.NXmonochromator(energy=root['energy'],
                         crystal=mono_crystal)


    inst['i0'] = nexus.NXdetector(data=dat.i0, description='Ion Chamber')
    inst['ifluor'] = nexus.NXdetector(data=dat.ifluor, description='Ion Chamber')

    fpath = Path(filename)
    outfile = fpath.stem + '_new' + fpath.suffix

    write_ascii(outfile, *coldata,  header=header,  label =collabel)

    print(f"done. Wrote group {entry_name} and file {outfile}")


################

metadata = {'sample': {'name': 'fe010'},
            'element': {'symbol': 'Fe', 'edge': 'K'},
            'monochromator': {'crystal': 'Si 111', 'd_spacing':  3.1551},
            'facility': {'name': 'Photon Factory', 'beamline': 'BL9A'},
            'detector': {'i0': '20 cm, He',
                         'ifluor':  'Vortex ME-4'},
                         }

nxroot = nexus.nxopen('Fe_XAS_PF9A_nexus.h5', 'w')

kekpf2nexus('PF9A_2022.dat', nxroot, entry_name='fe010', metadata=metadata)
