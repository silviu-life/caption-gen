def group_words(
    words: list[dict],
    max_per_page: int = 5,
    gap_threshold: float = 0.3,
) -> list[list[dict]]:
    if not words:
        return []

    pages: list[list[dict]] = []
    current: list[dict] = []

    for i, word in enumerate(words):
        current.append(word)

        is_last = i == len(words) - 1
        at_max = len(current) >= max_per_page
        has_gap = not is_last and words[i + 1]["start"] - word["end"] > gap_threshold

        if is_last:
            pages.append(current)
            current = []
        elif at_max or has_gap:
            if len(current) >= 2:
                pages.append(current)
                current = []

    if len(pages) > 1 and len(pages[-1]) == 1:
        single = pages.pop()
        pages[-1].extend(single)

    return pages
