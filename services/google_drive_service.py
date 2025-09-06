import requests

def download_from_gdrive(gdrive_url: str, output_file: str) -> str:
    """
    Download video from Google Drive public link.
    Returns local file path.
    """
    # Handle different types of Google Drive URLs
    if "drive.google.com" in gdrive_url:
        if "id=" in gdrive_url:
            file_id = gdrive_url.split("id=")[-1]
        elif "/d/" in gdrive_url:
            file_id = gdrive_url.split("/d/")[1].split("/")[0]
        else:
            raise ValueError("Invalid Google Drive URL format")

        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            with open(output_file, "wb") as f:
                for chunk in response.iter_content(1024 * 1024):
                    f.write(chunk)
            return output_file
        else:
            raise Exception(f"Failed to download file: {response.status_code}")
    else:
        raise ValueError("Provided URL is not a valid Google Drive link")