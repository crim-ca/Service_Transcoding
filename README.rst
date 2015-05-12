=======================================
Service Transcoding
=======================================

This is a worker which is used together with the MSS service https://github.com/crim-ca/mss.
It is used to convert pretty much any video format into:

 * High quality mp4 for streaming (H.264)
 * Low quality mp4 for streaming (H.264)
 * mp4 Video with no sound (H.264)
 * 8K single channel wav audio
 * Big jpg thumbnail
 * Small jpg thumbnail (x240)

This is a meta - project bringing together a transcoding package and a
connector to talk with the AMQP implementation for the Vesta project.

----------------
License
---------------

see https://github.com/crim-ca/Service_Transcoding/tree/master/THIRD_PARTY_LICENSES.rst

-----------------
Installation
-----------------
::

        sudo pip install requirements.pip


-----------------
Usage
-----------------

To start a worker, use the following command::

  celery worker -A Service_Transcoding.worker -l INFO -c 1 -E --config=celeryconfig -Q transcoder -n transcoder.%n

celeryconfig is a configuration file. Use example_celeryconfig.py as example.



