
import tempfile
import os

import yt_dlp
from mutagen import File as MutagenFile

from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import render
from django.conf import  settings

from ..decorators import auth_user


@auth_user
def music_download(request, user):
    if user.username not in settings.MUSIC_USER_ACCESS.split(","):
        messages.warning(request, 'Unauthorized access!!!')
        return HttpResponseRedirect("/")

    if request.method == 'POST':
        url = request.POST.get('doc_url')
        doc_type = request.POST.get('doc_type',"WEBM")
        ext = "mp3" if doc_type == "MP3" else "webm"

        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, f'temp.{ext}')

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'quiet': True,
                'postprocessors': []  # No conversion
            }

            try:
                # Download using yt_dlp
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)

                # Validate downloaded file
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    messages.error(request, 'Failed to download audio due to file error.')
                    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

                # Extract metadata
                audio = MutagenFile(output_path) if ext == "webm" else None
                audio_info = audio.info if audio else None

                bitrate = round(audio_info.bitrate / 1000, 2) if hasattr(audio_info, 'bitrate') else 'N/A'
                sample_rate = audio_info.sample_rate if hasattr(audio_info, 'sample_rate') else 'N/A'
                channels = audio_info.channels if hasattr(audio_info, 'channels') else 'N/A'
                length = round(audio_info.length, 2) if hasattr(audio_info, 'length') else 'N/A'
                codec = type(audio_info).__name__ if audio_info else 'Unknown'

                # Create filename
                title = info.get('title', 'audio')
                filename = f"{title}.{ext}"

                # Read file into memory
                with open(output_path, 'rb') as f:
                    file_data = f.read() 

                # Create response
                response = HttpResponse(file_data, content_type='audio/{ext}')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'

                # Optional: Set audio metadata in response headers
                response['X-Audio-Bitrate'] = str(bitrate)
                response['X-Audio-Sample-Rate'] = str(sample_rate)
                response['X-Audio-Channels'] = str(channels)
                response['X-Audio-Length'] = str(length)
                response['X-Audio-Codec'] = codec

                return response

            except Exception as e:
                messages.error(request, f'Failed to download audio: {str(e)}')

    return render(request, "music_downloader/yt_downloader.html", context={"user":user})