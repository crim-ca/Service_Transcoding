This is a meta - project bringing together a transcoding package and a
connector to talk with the AMQP implementation for the Vesta project.

To start a worker, use the following command::

  celery worker -A Service_Transcoding.worker -l INFO -c 1 -E --config=celeryconfig -Q transcoder -n transcoder.%n
