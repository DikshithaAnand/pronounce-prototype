import requests

BASE_URL = "http://localhost:8000"


def create_user(username: str):
    """
    Calls POST /users/
    """
    return requests.post(
        f"{BASE_URL}/users/",
        json={"username": username},
        timeout=10
    )


def get_passage(language: str):
    """
    Calls GET /get-passage/
    """
    return requests.get(
        f"{BASE_URL}/get-passage/",
        params={"language": language},
        timeout=10
    )


def process_audio(files, data):
    """
    Calls POST /process-audio/
    """
    return requests.post(
        f"{BASE_URL}/process-audio/",
        files=files,
        data=data,
        timeout=120
    )
