import json
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi

def get_video_id(youtube_url: str) -> str:
    """Extracts the video ID from a YouTube URL."""
    parsed = urlparse(youtube_url)
    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed.query)["v"][0]
    if parsed.hostname == "youtu.be":
        return parsed.path[1:]
    raise ValueError(f"Invalid YouTube URL: {youtube_url}")

def format_time(seconds: float) -> str:
    """Converts seconds to 'HH:MM:SS.ss' string format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"

def fetch_and_clean_transcript(youtube_url: str) -> str:
    """
    Fetches the transcript for a YouTube video and saves it with non-overlapping timestamps.
    
    Args:
        youtube_url (str): The full YouTube video URL.
        output_file (str): File path to save the cleaned transcript.
    """
    video_id = get_video_id(youtube_url)
    print(f"Fetching transcript for video ID: {video_id}")

    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id, languages=['en'])

    formatted_lines = []
    prev_end = 0.0
    for seg in transcript:
        text = seg.text.strip()
        if text.lower() in ["[music]", "foreign", ""]:
            continue
        start_time = max(seg.start, prev_end)
        end_time = start_time + seg.duration
        formatted_lines.append(f"[{start_time:.2f} → {end_time:.2f}] {text}")
        prev_end = end_time

    formatted_text = "\n".join(formatted_lines)
    return formatted_text

# Example usage
# if __name__ == "__main__":
#     url = "https://www.youtube.com/watch?v=qZfO4EopfPA&list=PL4cUxeGkcC9g8YFseGdkyj9RH9kVs_cMr&index=2"
#     fetch_and_clean_transcript(url)