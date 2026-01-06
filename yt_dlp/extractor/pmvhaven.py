import json
import re

from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class PMVHavenIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pmvhaven\.com/video/(?:[\w-]+_)?(?P<id>[a-f0-9]{24})'
    
    _TESTS = [{
        'url': 'https://pmvhaven.com/video/NEW-RULES_66799ca1ca817a3e12107c75',
        'info_dict': {
            'id': '66799ca1ca817a3e12107c75',
            'ext': 'mp4',
            'title': 'NEW RULES',
            'uploader': 'wombatpmv',
            'upload_date': '20240624',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        
        # 1. Get metadata from the new API endpoint you discovered
        api_url = f'https://pmvhaven.com/api/videos/{video_id}/watch-page'
        api_data = self._download_json(api_url, video_id, fatal=False) or {}
        
        video_meta = traverse_obj(api_data, ('data', 'video')) or api_data.get('video') or {}

        # 2. Extract the HLS/M3U8 Streaming URL
        # We check the API first, then fall back to searching the webpage
        m3u8_url = url_or_none(video_meta.get('hlsUrl')) or url_or_none(video_meta.get('url'))
        
        webpage = None
        if not m3u8_url or '.m3u8' not in m3u8_url:
            webpage = self._download_webpage(url, video_id)
            # Search for anything ending in .m3u8 in the page source
            m3u8_url = self._search_regex(
                r'["\'](https?://[^"\']+\.m3u8(?:\?[^"\']*)?)["\']',
                webpage, 'm3u8 url', default=None)

        if not m3u8_url:
            # Last ditch effort: Look for a direct MP4 if it's an old video
            video_url = self._html_search_regex(
                r'src=["\']([^"\']+\.mp4)["\']', webpage or "", 'mp4 url', default=None)
            if video_url:
                formats = [{'url': self._proto_relative_url(video_url, 'https:')}]
            else:
                raise self.raise_no_formats('Could not find m3u8 or mp4 links', expected=True)
        else:
            # Let yt-dlp handle the HLS playlist
            formats = self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', entry_protocol='m3u8_native', m3u8_id='hls')

        # 3. Assemble Metadata
        title = video_meta.get('title') or self._og_search_title(webpage)
        
        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': video_meta.get('description') or self._og_search_description(webpage),
            'uploader': traverse_obj(video_meta, ('creator', 0)) or video_meta.get('uploader'),
            'timestamp': parse_iso8601(video_meta.get('uploadDate')),
            'thumbnail': video_meta.get('thumbnailUrl') or self._og_search_thumbnail(webpage),
            'tags': video_meta.get('tags'),
            'age_limit': 18,
        }

class PMVHavenProfileIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pmvhaven\.com/profile/(?P<id>[a-zA-Z0-9-_]+)'

    def _real_extract(self, url):
        profile_id = self._match_id(url)
        api_url = 'https://pmvhaven.com/api/v2/profileInput'
        
        def fetch_page(page_num):
            payload = {
                'mode': 'getProfileVideos' if page_num == 1 else 'GetMoreProfileVideos',
                'user': profile_id,
                'index': page_num
            }
            return self._download_json(
                api_url, profile_id, 
                note=f'Downloading page {page_num}',
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'text/plain;charset=UTF-8'}
            )

        entries = []
        page = 1
        data = fetch_page(page)
        total_count = data.get('count', 0)
        
        # Combine lists
        all_videos = data.get('videos', []) + data.get('processingVideos', [])
        
        while len(entries) < total_count:
            if not all_videos and page > 1:
                p_data = fetch_page(page)
                all_videos = p_data.get('data', [])
                if not all_videos: break

            for v in all_videos:
                v_id = v.get('_id')
                if not v_id: continue
                
                # Format URL for the PMVHavenIE to pick up
                slug = re.sub(r'[^\w-]', '', v.get('title', 'video').replace(' ', '-'))
                entries.append({
                    '_type': 'url',
                    'id': v_id,
                    'title': v.get('title'),
                    'url': f"https://pmvhaven.com/video/{slug}_{v_id}",
                    'uploader': profile_id,
                })
            
            all_videos = []
            page += 1

        return self.playlist_result(entries, profile_id, f"{profile_id}'s Profile")