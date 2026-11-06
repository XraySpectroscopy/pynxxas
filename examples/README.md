# Examples

Sample datasets and conversion scripts for creating NeXus-compliant files.

## Structure

- **`auto/`** — Standard-format XDI files that can be converted automatically using `nxxas-convert`. 
- **`manual/`** — Datasets requiring custom conversion logic. Each subfolder contains a `convert_to_nexus.py` script and its source data. These serve as proof-of-concept for handling non-standard beamline formats.
- **`pending/`** — Raw data files awaiting conversion scripts or implementation in `nxxas-convert`. 

## Converting all examples

```bash
./convert_to_nexus.sh
```

This runs the auto-converter on `auto/` and executes each `convert_to_nexus.py` in `manual/`.

## NeXus files

`auto/converted.nxs` contains one NeXus group per XDI file in `auto/`, written by `nxxas-convert`. Each `manual/` subfolder contains a NeXus file with the name of the subfolder, for example `manual/KEK_PFdata/KEK_PFdata.nxs`. These are generated from the source data and can be safely deleted and regenerated.
