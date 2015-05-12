#!/usr/bin/env python
# coding:utf-8

"""
Transition service module.
"""

# --Standard lib modules------------------------------------------------------
import logging
import re

# --Project specific----------------------------------------------------------
from .Service.Document import Document
from .ffmpegConverter import Converter
from .Service.request import Request
from .Service import RemoteAccess

# --3rd party modules----------------------------------------------------------
from celery import current_task
from celery import Celery

PROCESS_NAME = 'worker.transcoder'
APP = Celery(PROCESS_NAME)

LOGGER = logging.getLogger(__name__)

# -- Configuration -----------------------------------------------------------
VERSION_MAJOR = 0
VERSION_MINOR = 2
BUILD_NUMBER = 3
PROCESS_VERSION = '{0}.{1}.{2}'.format(VERSION_MAJOR,
                                       VERSION_MINOR,
                                       BUILD_NUMBER)


class TranscoderError(Exception):
    """
    Indicates that an error occurred during transcoding.
    """
    pass


def convert(document, upload_url, set_progress_cb, thumbnail_timecode=None):
    """
    Transcode document.
    """
    stream_hd_opt = {
        'format': 'mp4',
        'audio': {
            'codec': 'aac',
            'bitrate': 192,
            'samplerate': 44100,
            'channels': 2
        },
        'video': {
            'codec': 'h264',
            'bitrate': 5000,
            'preset': 'fast',
            'profile': 'main',
            'height': 1080
        }
    }
    stream_sd_opt = {
        'format': 'mp4',
        'audio': {
            'codec': 'aac',
            'bitrate': 192,
            'samplerate': 44100,
            'channels': 2
        },
        'video': {
            'codec': 'h264',
            'bitrate': 1200,
            'preset': 'fast',
            'profile': 'main',
            'height': 480
        }
    }
    annot_video_opt = {
        'format': 'mp4',
        'video': {
            'codec': 'h264',
            'preset': 'fast',
            'profile': 'main'
        }
    }
    annot_audio_opt = {
        'format': 'wav',
        'audio': {
            'codec': 'pcm16',
            'samplerate': 8000,
            'channels': 1
        }
    }
    thumbnail_opt = {
        'format': 'jpg',
        'size': None
    }
    small_thumbnail_opt = {
        'format': 'jpg',
        'size': '*x240'
    }
    conversion_tasks = {'annot_audio':
                        {'cpu_time': 5, 'opt': annot_audio_opt},
                        'stream_sd':
                        {'cpu_time': 10, 'opt': stream_sd_opt},
                        'stream_hd':
                        {'cpu_time': 35, 'opt': stream_hd_opt},
                        'annot_video':
                        {'cpu_time': 35, 'opt': annot_video_opt},
                        'thumbnail':
                        {'cpu_time': 0, 'opt': thumbnail_opt},
                        'small_thumbnail':
                        {'cpu_time': 0, 'opt': small_thumbnail_opt}}

    LOGGER.info(u"Transcoding started for video {fn}".format(fn=document))

    converted_document = dict()
    document_basename = document.rsplit('.', 1)[0]

    converter = Converter()
    info = converter.probe(document)

    if info is None:
        raise TranscoderError('Video must have at least one audio or video '
                              'stream')

    audio_stream = info.audio
    video_stream = info.video

    # In case that the stream itself hasn't a valid duration take the duration
    # from the format structure
    for stream in [audio_stream, video_stream]:
        if stream.duration < info.format.duration and stream.duration < 0.01:
            stream.duration = info.format.duration

    if not audio_stream and not video_stream:
        raise TranscoderError('Video must have at least one audio or video '
                              'stream')

    # No thumbnail timecode; remove the thumbnail task
    if thumbnail_timecode is None:
        conversion_tasks.pop('thumbnail')
        conversion_tasks.pop('small_thumbnail')
    # No audio stream; remove audio related tasks
    if not audio_stream:
        conversion_tasks.pop('annot_audio')
    # No video stream; remove video related tasks
    if not video_stream:
        conversion_tasks.pop('stream_hd')
        conversion_tasks.pop('stream_sd')
        conversion_tasks.pop('annot_video')
        conversion_tasks.pop('thumbnail')
        conversion_tasks.pop('small_thumbnail')

        if audio_stream:
            # Extract length from audio stream
            converted_document['length'] = str(audio_stream.duration)
    else:
        # Extract length from video stream and add also the framerate
        converted_document['length'] = str(video_stream.duration)
        converted_document['framerate'] = str(video_stream.video_fps)

        # If a thumbnail tc is given bounds it to the actual video length
        if thumbnail_timecode is not None:
            if thumbnail_timecode < 0 or \
               thumbnail_timecode >= video_stream.duration:
                thumbnail_timecode = video_stream.duration * 0.05

        # If the video height is less than sd,
        # limit the sd height and remove hd task
        if video_stream.video_height <= stream_sd_opt['video']['height']:
            stream_sd_opt['video']['height'] = video_stream.video_height
            conversion_tasks.pop('stream_hd')
        # If the video height is less than hd, limit the hd height
        elif video_stream.video_height < stream_hd_opt['video']['height']:
            stream_hd_opt['video']['height'] = video_stream.video_height

        # annot video will use the stream_hd video
        conversion_tasks.pop('annot_video')

    cur_progress = 0
    total_cpu_time = 0

    for task in conversion_tasks:
        total_cpu_time += conversion_tasks[task]['cpu_time']

    for task in conversion_tasks:
        task_cpu_time = conversion_tasks[task]['cpu_time']

        filename = ('{in_fn}_{task}.{ext}'.
                    format(in_fn=document_basename,
                           task=task,
                           ext=conversion_tasks[task]['opt']['format']))

        LOGGER.info(u"Transcoding video {in_fn} to {out_fn} for {task}".
                    format(in_fn=document,
                           out_fn=filename,
                           task=task))

        if conversion_tasks[task]['opt']['format'] == 'jpg':
            size = conversion_tasks[task]['opt']['size']
            if size:
                match = re.search('([0-9*]*)x([0-9*]*)', size)
                if match:
                    if match.group(1) == '*' and match.group(2) != '*':
                        size = '{0}x{1}'.format(
                            int(match.group(2)) * video_stream.video_width /
                            video_stream.video_height,
                            match.group(2))
                    elif match.group(2) == '*' and match.group(1) != '*':
                        size = '{0}x{1}'.format(
                            match.group(1),
                            int(match.group(1)) * video_stream.video_height /
                            video_stream.video_width)
                    else:
                        size = None
                else:
                    size = None

            converter.thumbnail(document, thumbnail_timecode, filename, size)
        else:
            # Convert document to a
            # normalized document ready for a specific task
            conv = converter.convert(document, filename,
                                     conversion_tasks[task]['opt'],
                                     timeout=25,
                                     nb_threads=4)

            for timecode in conv:
                rel_progress = timecode * task_cpu_time / total_cpu_time
                progress = min(100, max(0, int(cur_progress + rel_progress)))
                LOGGER.info(u"Set progress to {0}% in celery".
                            format(progress))
                set_progress_cb(progress)
                LOGGER.info(u"Set progress done in celery")

        # Upload the normalized document
        uploaded_document = RemoteAccess.upload(Document(upload_url, filename))
        converted_document[task] = uploaded_document.url

        LOGGER.info(u"Destroying local transcoded document => {0}"
                    .format(filename))

        RemoteAccess.cleanup(uploaded_document)

        cur_progress += 100 * task_cpu_time / total_cpu_time

    if 'stream_hd' in converted_document:
        converted_document['annot_video'] = converted_document['stream_hd']
    elif 'stream_sd' in converted_document:
        converted_document['annot_video'] = converted_document['stream_sd']

    return converted_document


@APP.task(name=PROCESS_NAME)
def process(body):
    """
    Actual transcoder processing wrapper function.

    :param body: Body of the request as defined by the Vesta Workgroup.
    :returns: Dict of converted media unique urls on the vesta storage
    """

    if not current_task:
        LOGGER.warning(u"Could not get handle on current task instance")
    else:
        LOGGER.debug(u"Got handle on current task instance")

    # The video filename is available here : request.document
    request = Request(body, current_task)
    request.process_version = PROCESS_VERSION

    # TODO Wrap this field in a class that could be used also by SSM
    # to avoid hardcoding the filed name
    ttc = None
    if not request.misc or 'upload_url' not in request.misc:
        LOGGER.error(u"No upload url provided in task")
        raise TranscoderError("No upload url provided in task")

    if 'thumbnail_timecode' in request.misc:
        ttc = request.misc['thumbnail_timecode']
        if bool(ttc):
            ttc = float(ttc)
            LOGGER.info(u"Task contains a thumbnail timecode : {ttc}".
                        format(ttc=ttc))

    return convert(request.document.local_path,
                   request.misc['upload_url'],
                   request.set_progress,
                   ttc)
