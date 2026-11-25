import unicodedata


def merge_overlap(previous: str, incoming: str) -> str:
    """Remove only a contiguous suffix/prefix match, not legitimate repetitions elsewhere."""
    left, right = previous.split(), incoming.split()

    def normalize(word):
        return "".join(
            char
            for char in unicodedata.normalize("NFC", word)
            if not unicodedata.category(char).startswith(("P", "S"))
        ).casefold()

    for count in range(min(len(left), len(right), 80), 0, -1):
        if [normalize(x) for x in left[-count:]] == [normalize(x) for x in right[:count]]:
            return " ".join(left + right[count:])
    return " ".join(left + right)
