def choose_release(releases, expected, interactive=False):
    if not releases:
        return None

    if not interactive:
        return releases[0]

    for i, r in enumerate(releases, start=1):
        title = r.get("title")
        date = r.get("date", "unknown")
        print(f"{i}: {title} ({date})")

    choice = input("Choose release number (or blank to abort): ").strip()
    if not choice:
        return None

    try:
        return releases[int(choice) - 1]
    except (ValueError, IndexError):
        return None


def extract_metadata(release):
    tracks = []
    for medium in release.get("medium-list", []):
        for track in medium.get("track-list", []):
            tracks.append(track["recording"]["title"])

    return {
        "title": release.get("title"),
        "author": ", ".join(a["name"] for a in release["artist-credit"]),
        "tracks": tracks,
        "musicbrainz_id": release.get("id"),
    }
