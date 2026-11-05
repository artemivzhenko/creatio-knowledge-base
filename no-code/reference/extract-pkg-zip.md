---
command: extract-pkg-zip
block: clio-packages
source: clio 8.1.0.145, clio/docs/commands/extract-pkg-zip.md (MIT)
---
# extract-pkg-zip - extract-pkg-zip

## Name

extract-pkg-zip


## Description

extract-pkg-zip command unzip package from *.gz archive to directory
that contain package folder


## Options

```bash
Package name (pos. 0)    Name/path of package acrhive file

--DestinationPath       -d  Destionation path for extract package (Optional)
```


## Example

```bash
clio extract-pkg-zip MyPackage
extract-pkg-zip MyPackage.gz in current folder to directory MyPackage in current folder

clio extract-pkg-zip c:\MyPackage.gz -f c:\App\Pkg
extract-pkg-zip MyPackage.gz file to c:\App\MyPackage folder
```
