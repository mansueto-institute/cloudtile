# cloudtile

![Main Branch Tests](https://github.com/mansueto-institute/cloudtile/actions/workflows/build.yml/badge.svg?branch=main)

Python tool for converting vector file formats to pmtiles files by scheduling jobs on the cloud.

## Supported VectorFiles

- Convert (either locally, on a docker file, or on AWS ECS)
  - `{.geojson, .parquet, .gpkg}` -> `fgb`.
  - `.pmtiles` -> `.pmtiles`.
- Upload files to S3
- Download files from S3

All the files are hosted in S3 within the bucket: `cloudtile-files`.

## Installation

You can install the package two ways, please make sure to read the section on [dependencies](#dependencies)

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

## Dependencies

### Completely Local

If you want to run the code completely locally, you have to install its external dependencies:

#### External Dependencies

- [GDAL](https://gdal.org/download.html)
- [tippecanoe](https://github.com/felt/tippecanoe)

You can refer to our [Dockerfile](Dockerfile) to reference installation instructions for installing the [external dependencies](#external-dependencies). These are also found in their respective repositories.

We install `gdal` using their Docker image, however if you want to install everything locally, you can install `gdal` via [`conda`](https://gdal.org/download.html#conda) making sure you install the `libgdal-arrow-parquet` if you'd like to convert a file starting from a `.parquet` file.

### Docker

Some of these dependencies are hard to install manually, so instead you can run the the code within a Docker container. You can use the [Dockerfile](Dockerfile) included in the package to first build the Docker image and then run it on a local container.

You would do this by first building the image:

``` bash
docker build -t cloudtile:latest .
```

And then running it (notice the passing of CLI arguments):

``` bash
docker run --rm --env-file=.env cloudtile:latest convert single-step blocks_SLE.parquet 5 9
```

Notice here that you will either have to mount a [Docker volume](https://stackoverflow.com/a/41092636/8998223) or you will have to copy the file into the container using the `COPY` command in the Dockerfile and also remove it from the `.dockerignore` file. Of course this is only when you want to put a file from your local file system into the container. It might be easier to first upload it to S3 and then run the same Docker conversion but using the `--s3` flag (see below).

Or if you want to use S3 storage:

``` bash
docker run --env-file .env --rm cloudtile:latest convert single-step blocks_SLE.parquet 5 9 --s3
```

Notice in the last example that we are passing AWS credentials as environment variables via the `--env-file=.env` file. This is necessary for allowing the container to access your AWS account.

## Usage

The main way of using the package is to use its CLI. After installation, you have access to the CLI via the `cloudtile` command in your terminal. You can get help by passing the `-h` or `--help` flag:

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

You can do the same for sub-commands, for example:

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
>>> cloudtile convert fgb2pmtiles -h
usage: cloudtile convert fgb2pmtiles [-h] [--s3 | --ecs] [--memory MEMORY] [--storage STORAGE] [--config CONFIG] filename min_zoom max_zoom

positional arguments:
  filename           The file name to convert
  min_zoom           The minimum zoom level to use in the conversion
  max_zoom           The maximum zoom level to use in the conversion

optional arguments:
  -h, --help         show this help message and exit
  --s3               Whether to use a remote file or use S3
  --ecs              Whether to run the entire job on AWS ECS
  --memory MEMORY    Whether to override the 64GB memory limit. Must be only be used with the --ecs flag. Additionally, the values must be within the range of [32768, 122880] in increments
                     of 8192.
  --storage STORAGE  Whether to override the 100GB ephemeral storage default. Must only be used with the --ecs flag. Additionally, values must be within the range of 20 and 200 (GiBs)
  --config CONFIG    The path to a config file for tippecanoe. If not passed the default config file is used.
```

### AWS Credentials

Make sure that if you want to use the `--s3` flag or the `--ecs` flag that you have the infrastructure setup and that you have credentials as environment variables set on your terminal session, otherwise you will not be able to access the AWS resources needed.

## CDK

We use the [`aws-cdk`](https://docs.aws.amazon.com/cdk/v2/guide/home.html#why_use_cdk) for defining, creating, updating and destroying the AWS infrastructure that is used by the application. The `cdk` code can be found in the `cdk` sub-module in the main package.

In order to use the `aws-cdk` CLI you will need to [install it](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_install), and check for its [prerequisites](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_prerequisites).

After installing it, you can synthesize the current stack by running `cdk synth`, this will return a CloudFormation configuration file. You can create the stack by running `cdk deploy`. If you make any changes to the stack and would like to update your stack, you can run `cdk diff` to check for the changes (not necessary), and then run `cdk deploy` to update it. If you'd like to tear down the stack, you can run `cdk destroy`.

If you would like to setup the stack on your own AWS account for the first time, you will need to [bootstrap](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_bootstrap) it.

## Managing

### Uploading

You can upload files from your local machine by running:

``` bash
cloudtile manage upload myfile.parquet
```

If the file is already there (and it has the same hash) you will get a warning informing you that the file is already there. Also you don't have to worry any of the bucket prefixes. The application shares a single bucket for all files and uploads them into their respective sub paths automatically, based on the file suffix.

### Downloading

You can download files from S3 to your local machine by running:

``` bash
cloudtile manage download myfile.pmtiles .
```

Make sure to check the help by running:

``` bash
cloudtile manage download -h
```

## Conversion

There are three *modes* of converting files:

1. [Fully Local](#fully-local): input, compute, and output are done locally.
2. [Local-Compute](#local-compute): input and output are downloaded and uploaded from/to S3. While the compute is done locally.
3. [Fully-Remote](#fully-remote): everything is done in the cloud.
4. [Single-Step](#single-step): do all convert steps as a single call.

### Fully local

If you want to run a local job to convert a `.parquet` file into a `.fgb` (where the `.parquet` file is in your local machine and you want the `.fgb` to be outputted in the same directory as the input file), then you can run this:

``` bash
cloudtile convert vector2fgb myfile.parquet
```

This will create a file `myfile.fgb` in the same directory as the input file.

### Local Compute

If you want to use a file that exists in S3, do the conversion in your local machine, and then upload the file to S3, then you can use the same command as in [fully local](#fully-local) but with the added flag of `--s3` like this:

``` bash
cloudtile convert vector2fgb --s3 myfile.parquet
```

Of course the file `myfile.parquet` must be hosted on S3 for this to work! See [uploading](#uploading) for instructions how to upload files.

### Fully Remote

If you already uploaded a file (see [uploading](#uploading)) and you want to run a job on the cloud, then you can use the same command as in [fully local](#fully-local) but with the added flag of `--ecs` like this:

``` bash
cloudtile convert vector2fgb --ecs myfile.parquet
```

This, again, will only work if the file is already in S3 (see [uploading](#uploading))

Running the command will submit a task to the ECS cluster and run the download, conversion and upload on a docker container. When you run the command, you will get the `.json` response from the ECS API printer in your terminal that can help you track down the running task on the ECS dashboard on the AWS console. Currently there is no method of notification to notify you that the job has finished.

### Single-Step

If you want to convert a [supported file](#supported-vectorfiles) or a `.fgb` file into a `.pmtiles` directly, you can use the `single-step` convert sub-command. You will have to state which zoom level you want `tippecanoe` to use. You can call the CLI like so (where 2 and 9 are `min_zoom` and `max_zoom`, check out the help for more info):

[Fully Local](#fully-local) mode:

``` bash
cloudtile convert single-step blocks_SLE.parquet 2 9
```

[Local Compute](#local-compute) mode:

``` bash
cloudtile convert single-step --s3 blocks_SLE.parquet 2 9
```

[Fully Remote](#fully-remote) mode:

``` bash
cloudtile convert single-step --ecs blocks_SLE.parquet 2 9
```

### Tippecanoe Settings

#### Using a `.yaml` file

There are some opinionated default settings that Tippecanoe uses in `/src/cloudtile/tiles_config.yaml`, which are used by default. If you would like use a different configuration file, you can pass the path to it using the `--config` optional argument. The `--config` optional argument is only exposed either in the `single-step` or in the `fgb2pmtiles` convert sub command, since these are the only conversions that use Tippecanoe. You can pass it like this for example:

``` bash
cloudtile convert fgb2pmtiles --config /dir/myconfig.yaml myfile.fgb 5 10
```

Or via the single-step conversion from a `.fgb` file

``` bash
cloudtile convert single-step --config /dir/myconfig.yaml myfile.fgb 5 10
```

Or via the single-step conversion from a vectorfile:

``` bash
cloudtile convert single-step --config /dir/myconfig.yaml myfile.parquet 5 10
```

#### Passing settings directly

You can also pass settings directly to `tippecanoe` via the `--tc-kwargs` optional command in the CLI. The settings in the default `tippecanoe.yaml` file will always be applied, unless overridden. If you pass a setting not present in the defaults then it will be added to the defaults.

For example, the `--force` setting defaults to `True` in [tippecanoe.yaml](/src/cloudtile/tippecanoe.yaml). If you want to override this setting, you can pass:

``` bash
cloudtile convert single-step blocks_SLE.parquet 9 g --tc-kwargs force=False
```

This language of `--tc-kwargs setting=False` is only needed to override default settings that are `True`. For example, if you want to add a *new* setting `--hilbert` as `True` you can pass:

``` bash
cloudtile convert single-step blocks_SLE.parquet 9 g --tc-kwargs hilbert
```

You can also pass these settings to an [ECS](#fully-remote) task like so:

``` bash
cloudtile convert single-step regions_map.parquet 9 g --ecs --tc-kwargs coalesce-densest-as-needed extend-zooms-if-still-dropping visvalingam
```