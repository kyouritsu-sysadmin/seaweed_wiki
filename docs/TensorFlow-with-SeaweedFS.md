---
id: TensorFlow-with-SeaweedFS
title: "TensorFlow with SeaweedFS"
sidebar_label: "TensorFlow with SeaweedFS"
---

# Simplest Example
```
import tensorflow as tf
import os

os.environ["S3_ENDPOINT"] = "http://localhost:8333"

# ...

train_dataset = tf.data.TFRecordDataset(filenames=[
    "s3://bucketname/path/to/file1.tfrecord",
    "s3://bucketname/path/to/file2.tfrecord",
]).map(record_parser).batch(BATCH_SIZE)

# ...

model.fit(train_dataset, ...)

```
# TensorFlow on SeaweedFS S3
[TensorFlow already supports S3](https://github.com/tensorflow/examples/blame/tflmm/v0.2.4/community/en/docs/deploy/s3.md) (Old Link)

Here is an adaption of it with unnecessary content removed.

## Configuration

When reading or writing data on S3 with your TensorFlow program, the behavior
can be controlled by various environmental variables:

*   **S3_ENDPOINT**: The endpoint could be overridden explicitly with
    `S3_ENDPOINT` specified.

To read or write objects in a bucket that is not publicly accessible,
AWS credentials must be provided through one of the following methods:

*   Set credentials in the AWS credentials profile file on the local system,
    located at: `~/.aws/credentials` on Linux, macOS, or Unix, or
    `C:\Users\USERNAME\.aws\credentials` on Windows.
*   Set the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment
    variables.

## Example Setup

Using the above information, we can configure Tensorflow to communicate to an S3
endpoint by setting the following environment variables:

```bash
S3_ENDPOINT=http://localhost:8333
AWS_ACCESS_KEY_ID=XXXXX                 # Credentials if configured
AWS_SECRET_ACCESS_KEY=XXXXX

```

## Usage

Once setup is completed, Tensorflow can interact with S3 in a variety of ways.
Anywhere there is a Tensorflow IO function, an S3 URL can be used.

### Smoke Test

To test your setup, stat a file:

```python
from tensorflow.python.lib.io import file_io
print file_io.stat('s3://bucketname/path/')
```

You should see output similar to this:

```console
<tensorflow.python.pywrap_tensorflow_internal.FileStatistics; proxy of <Swig Object of type 'tensorflow::FileStatistics *' at 0x10c2171b0> >
```

### Reading Data

```python
filenames = ["s3://bucketname/path/to/file1.tfrecord",
             "s3://bucketname/path/to/file2.tfrecord"]
dataset = tf.data.TFRecordDataset(filenames)
```

### Tensorflow Tools

Many Tensorflow tools, such as Tensorboard or model serving, can also take S3
URLS as arguments:

```bash
tensorboard --logdir s3://bucketname/path/to/model/
tensorflow_model_server --port=9000 --model_name=model --model_base_path=s3://bucketname/path/to/model/export/
```

This enables an end to end workflow using S3 for all data needs.


