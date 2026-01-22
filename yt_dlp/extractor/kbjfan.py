from .common import InfoExtractor
from ..utils import (
    clean_html,
    parse_duration,
    unified_timestamp,
)


class KBJFanIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?kbjfan\.com/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<id>[^/]+)/?'
    _TESTS = [{
        'url': 'https://www.kbjfan.com/2026/01/20/korean-bj-13457457832-2025-10-13/',
        'info_dict': {
            'id': 'korean-bj-13457457832-2025-10-13',
            'ext': 'mp4',
            'title': '[Korean BJ] 13457457832 2025-10-13',
            'uploader': '13457457832(❤️구름❤️)',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        
        webpage = self._download_webpage(url, video_id)
        
        # Extract video URL from the video tag
        video_url = self._html_search_regex(
            r'<video[^>]+src=["\']([^"\']+)["\']',
            webpage, 'video URL', default=None)
        
        if not video_url:
            # Alternative: search for videosnoerroranymore.com domain in page source
            video_url = self._search_regex(
                r'(https?://[^"\']+videosnoerroranymore\.com/videos/[^"\']+\.mp4)',
                webpage, 'video URL')
        
        # Extract title
        title = self._html_search_meta(
            ['og:title', 'twitter:title'],
            webpage, 'title', default=None)
        if not title:
            title = self._html_search_regex(
                r'<h1[^>]*>([^<]+)</h1>',
                webpage, 'title', default=video_id)
        
        # Clean title (remove " - KBJFan" suffix if present)
        if title:
            title = title.replace(' - KBJFan', '').strip()
        
        # Extract thumbnail from poster attribute
        thumbnail = self._html_search_regex(
            r'<video[^>]+poster=["\']([^"\']+)["\']',
            webpage, 'thumbnail', default=None)
        
        # Extract metadata from the video info section
        uploader = self._search_regex(
            r'BJ Name:\s*</strong>\s*([^<\n]+)',
            webpage, 'uploader', default=None)
        
        platform = self._search_regex(
            r'Platform:\s*</strong>\s*([^<\n]+)',
            webpage, 'platform', default=None)
        
        upload_date = self._search_regex(
            r'Live Date:\s*</strong>\s*(\d{4}-\d{2}-\d{2})',
            webpage, 'upload date', default=None)
        
        duration_str = self._search_regex(
            r'Video Duration:\s*</strong>\s*([^<\n]+)',
            webpage, 'duration', default=None)
        
        duration = parse_duration(duration_str) if duration_str else None
        
        # Convert upload_date to unified format (YYYYMMDD)
        timestamp = None
        if upload_date:
            timestamp = unified_timestamp(upload_date)
            upload_date = upload_date.replace('-', '')
        
        # Extract description
        description = self._html_search_meta(
            ['og:description', 'twitter:description', 'description'],
            webpage, 'description', default=None)
        
        if description:
            description = clean_html(description)
        
        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'upload_date': upload_date,
            'timestamp': timestamp,
            'duration': duration,
            'description': description,
            'ext': 'mp4',
            'http_headers': {
                'Referer': url,
            },
            'platform': platform,
        }
