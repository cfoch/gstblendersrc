# GstBlenderSrc

***This is a GStreamer element to stream frames from a blender file using  [BlenderAsPyModule](https://wiki.blender.org/index.php/User:Ideasman42/BlenderAsPyModule)***

To use this plugin, first you will have to set the **GST_PLUGIN_PATH**

```
export GST_PLUGIN_PATH=/location/of/file/one/level/before_the_python_dir/:$GST_PLUGIN_PATH
```

Example:
```
gst-launch-1.0 blendersrc location="foo.blend"  output-location="/tmp/" \
start-frame=120 end-frame=80 ! decodebin ! videoconvert ! autovideosink
```
