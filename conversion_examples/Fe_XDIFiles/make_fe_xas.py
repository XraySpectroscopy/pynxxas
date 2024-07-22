from  nexusformat import nexus
from pathlib import Path
import h5py
import json
import numpy as np
from larch.xafs import pre_edge
from larch.io import read_xdi, read_ascii, write_ascii
from larch.utils import gformat


def xdi2nexus(filename, nxroot, entry_name='entry',
              data_mode='transmission'):

    asc = read_ascii(filename)
    dat = read_xdi(filename)
    filename = Path(filename).name

    dat.energy
    dat.mu = dat.mutrans*1.0
    dat.itrans = (dat.itrans*100.0).astype('int32')/100.0  # round
    dat.array_labels[dat.array_labels.index('mutrans')] = 'mu'

    pre_edge(dat, pre1=-150, pre2=-50, norm1=150, norm2=750)
    pre_offset = dat.pre_edge_details.pre_offset
    pre_slope = dat.pre_edge_details.pre_slope
    nvict = dat.pre_edge_details.nvict

    rawdata = np.zeros((len(dat.energy), 4), dtype='float64')
    rawdata[:, 0]  = dat.energy
    rawdata[:, 1]  = dat.norm
    rawdata[:, 2]  = (dat.itrans*10.0).astype('int32')/10.0
    rawdata[:, 3]  = dat.i0*1.0

    root = nxroot[entry_name] = nexus.NXentry()

    root['definition'] = 'NXxas'
    root['mode'] = 'transmission'
    root['element'] = dat.attrs['element']['symbol']
    root['absorption_edge'] = dat.attrs['element']['edge']
    root['energy']  = nexus.NXdata(dat.energy)
    root['energy'].attrs['units'] = 'eV'
    root['intensity']  = nexus.NXdata(dat.norm)

    plot = root['plot'] = nexus.NXdata()
    plot['energy'] = root['energy']
    plot['intensity'] = root['intensity']

    names = {}

    # sample
    sample = nexus.NXsample(chemical_formula='Fe')
    for aname, value in dat.attrs['sample'].items():
        setattr(sample, aname, value)
        if aname.lower() == 'name':
            names['sample'] = value


    #  process
    kwargs = ", ".join([f"{k}={v}" for k, v in dat.callargs.pre_edge.items()])

    preline = f"pre_edge = {gformat(pre_offset, 12)} + {gformat(pre_slope, 12)}*energy"
    if nvict != 0:
        preline = f"({preline})*energy(-{dat.nvict})"

    proc = ["processing done with xraylarch version 0.9.80",
            f"    larch.xafs.pre_edge(data, {kwargs})",
            "using 'data' from arrays in rawdata/signal",
            "energy = data[:,0]      # column 1: energy (eV)",
            "itrans = data[:, 2]     # column 3: transmitted beam intensity",
            "i0 = data[:, 3]         # column 4: incident beam intensity",
            "mu = -log(itrans/i0)    # absorbance",
             f"edge_step = {gformat(dat.edge_step, 12)}",
             preline,
            "intensity = norm = (mu - pre_edge) /edge_step"]

    notes='\n'.join(proc)

    header = ['XDI/1.1',
             'Column.1: energy eV', 'Column.2: norm', 'Column.3: itrans', 'Column.4: i0']
    end_header = []
    target = header
    for j in asc.header[4:]:
        if j.startswith('#'): j = j[1:].strip()
        if '---' in j:
            break
        if '///' in j:
            target = end_header
        target.append(j)

    header.append('Process.program: xraylarch')
    header.append('Process.version: 0.9.80')
    header.append(f'Process.command: pre_edge(data, {kwargs})')
    for i, p in enumerate(proc[3:]):
        header.append(f"Process.step{i+1:d}: {p}")
    for j in end_header:
        if j.startswith('#'): j = j[1:].strip()
        header.append(j)

    root['process'] = nexus.NXprocess(program='xraylarch', version='0.9.80',
                                      notes=notes)



    # rawdata
    root['rawdata'] = nexus.NXdata(rawdata)
    root['rawdata'].attrs['column_labels'] = json.dumps(["energy", "intensity", "itrans", "i0"])
    root['rawdata'].attrs['data_collector'] = 'Matthew Newville'
    root['rawdata'].attrs['filename'] = filename


    # scan
    scan = root['scan'] = nexus.NXcollection()
    scan.headers = json.dumps(dat.attrs)

    for key, val in dat.attrs['scan'].items():
        setattr(scan, key, val)
    if getattr(dat, 'comments', None) is not None:
        scan.comments =  dat.comments


    inst = root['instrument'] = nexus.NXinstrument()

    source = inst['source'] = nexus.NXsource(type='Synchrotron X-ray Source',
                                        probe='x-ray')

    if 'facility' in dat.attrs:
        for aname, value in dat.attrs['facility'].items():
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

    bl = inst['beamline'] = nexus.NXcollection()
    for aname, value in dat.attrs['beamline'].items():
        setattr(bl, aname, value)
        if aname.lower() == 'name':
            names['beamline'] = value


    title_words = [names.get('sample', filename),
                   names.get('facility', ''),
                   names.get('beamline', '')]
    root['title'] = (' '.join(title_words)).strip()


    # mono
    d_spacing = dat.attrs['mono'].get('d_spacing', 3.13550)
    mono_name = dat.attrs['mono'].get('name', 'Si 111')

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


    inst['i0'] = nexus.NXdetector(data=nexus.NXdata(dat.i0), description=dat.attrs['detector']['i0'])
    inst['itrans'] = nexus.NXdetector(data=nexus.NXdata(dat.itrans), description=dat.attrs['detector']['i1'])

    outfile = filename.replace('.xdi', '_new.xdi')
    write_ascii(outfile, dat.energy, dat.norm, dat.itrans, dat.i0,
               header=header,
               label = 'energy           norm             itrans           i0')

    print("done ", entry_name)



################
nxroot = nexus.nxopen('fe_xas_nexus.h5', 'w')

xdi2nexus('fe_metal_rt.xdi', nxroot, entry_name='fe_metal')
xdi2nexus('fe2o3_rt.xdi', nxroot, entry_name='fe2o3')
xdi2nexus('feo_rt1.xdi', nxroot, entry_name='feo')