# cloudtile

![Main Branch Tests](https://github.com/mansueto-institute/cloudtile/actions/workflows/build.yml/badge.svg?branch=main)

Python tool for converting vector file formats to pmtiles files by scheduling jobs on the cloud.

Features:

- Convert (either locally, on a docker file, or on AWS ECS)
  - `{.geojson, .parquet, .gpkg}` -> `fgb`.
  - `.fgb` -> `.mbtiles`.
  - `.mbtiles` -> `.pmtiles`.
- Upload files to S3
- Download files from S3

## Installation

You can install the package two ways:

Directly from the GitHub repository:

``` bash
pip install git+https://github.com/mansueto-institute/cloudtile
```

By cloning the repo:

``` bash
git clone https://github.com/mansueto-institute/cloudtile
pip install -e cloudtile
```

### Developing

If you'd like to contribute, it's suggested that you install the optional dependencies with the `[dev]` dynamic metadata for setuptools. You can do this by either:

``` bash
pip install "cloudtile[dev] @ git+https://github.com/mansueto-institute/cloudtile"
```

By cloning the repo:

``` bash
git clone https://github.com/mansueto-institute/cloudtile
pip install -e cloudtile[dev]
```

This will install linters and the requirements for running the tests. For more information as to what is done to the code for testing/linting refer to [GitHub Action](.github/workflows/build.yml).

## Usage

The main way of using the package is to use its CLI. After installation, you have access to the CLI via the `cloudtile` command in your terminal. You can get help by pasing the `-h` or `--help` flag:

``` bash
>>> cloudtile -h
usage: cloudtile manage [-h] management ...

positional arguments:
  management  The management actions available
    upload    Uploads a local file to S3
    download  Downloads a file from S3 a local directory.

optional arguments:
  -h, --help  show this help message and exit
```

You can do the same for subcommands, for example:

``` bash
>>> cloudtile manage -h
usage: cloudtile manage [-h] management ...

positional arguments:
  management  The management actions available
    upload    Uploads a local file to S3
    download  Downloads a file from S3 a local directory.

optional arguments:
  -h, --help  show this help message and exit
```

``` bash
cloudtile convert fgb2mbtiles -h
usage: cloudtile convert fgb2mbtiles [-h] [--s3 | --ecs] filename min_zoom max_zoom

positional arguments:
  filename    The file name to convert
  min_zoom    The minimum zoom level to use in the conversion
  max_zoom    The maximum zoom level to use in the conversion

optional arguments:
  -h, --help  show this help message and exit
  --s3        Whether to use a remote file or use S3
  --ecs       Whether to run the entire job on AWS ECS
```

### Conversion

There are three *modes* of converting files:

1. Fully local: input, compute, and output are done locally.
2. Local-Compute: input and output are downloaded and uploaded from/to S3. While the compute is done locally.
3. Fully-Remote: everything is done in the cloud.

#### Fully local

If you want to run a local job to convert a `.parquet` file into a `.fgb` (downloading the `.parquet` file from S3 and uploading the `.fgb` into S3) file you have to do the following:

``` bash
cloudtile convert vector2fgb myfile.parquet
```