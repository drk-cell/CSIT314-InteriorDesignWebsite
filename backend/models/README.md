# Tag model

`mobilenetv2-7.onnx` is MobileNetV2, trained on ImageNet, exported by the
[ONNX Model Zoo](https://github.com/onnx/models). It is 14 MB and runs on the
CPU through onnxruntime in about 40 ms per photo.

`synset.txt` holds the 1000 class names, one per line, in the order the model
outputs them.

Licence: Apache-2.0, inherited from the TensorFlow MobileNetV2 checkpoint. The
ONNX Model Zoo redistributes the export under the same terms.

## What it is used for

`app/services/object_labels.py` runs the model and keeps only the classes that
appear in `LABEL_TO_TAG`. Everything else is dropped, so a confident wrong guess
("throne", "vault", "photocopier") never becomes a tag.

## How to replace it

1. Export any 224x224 ImageNet-style classifier to ONNX.
2. Write its class names to `synset.txt`, one per line, without the synset id.
3. Point `APP_TAG_MODEL` at the file, or overwrite `mobilenetv2-7.onnx`.
4. Extend `LABEL_TO_TAG` with the labels worth showing.

The endpoint, the analyser and both screens read only `object_tags()`, so
nothing else changes.

## Removing it

Delete both files. `object_tags()` returns an empty list, the analyser falls
back to the colour tags, and the response reports `engine: "colour only"`.
