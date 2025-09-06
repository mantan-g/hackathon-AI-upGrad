import json
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter


def get_video_id(youtube_url: str) -> str:
    """
    Extracts the video ID from a YouTube URL.
    Supports normal YouTube and youtu.be short links.
    """
    parsed_url = urlparse(youtube_url)

    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed_url.query)["v"][0]
    elif parsed_url.hostname == "youtu.be":
        return parsed_url.path[1:]
    else:
        raise ValueError(f"Invalid YouTube URL: {youtube_url}")


def fetch_transcript(video_id: str, lang: str = "en") -> str:
    """
    Fetches transcript and returns as plain text.
    """
    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id, languages=[lang])

    formatter = TextFormatter()
    return formatter.format_transcript(transcript)


if __name__ == "__main__":
    # Load videos JSON
    with open("videosurl.json", "r") as f:
        videos = json.load(f)

    # Just take the first youtubeUrl for now
    youtube_url = videos[0]["youtubeUrl"]
    print(f"Fetching transcript for: {youtube_url}")

    video_id = get_video_id(youtube_url)
    transcript_text = fetch_transcript(video_id, lang="en")

    # Save transcript
    with open("transcript.txt", "w", encoding="utf-8") as f:
        f.write(transcript_text)

    print("✅ Transcript saved to transcript.txt")
