"""Extract room occupancy from the college's positioned timetable PDF grid."""
import re

import pdfplumber

from config import DAYS, SLOTS

# Column centers in the college's A4 Excel timetable (PDF points).
_COLUMN_CENTERS = [166, 189, 212, 235, 258, 281, 304, 327, 350, 373, 398, 421]
_COURSES = ["BCA A", "BCA B", "BCA C", "IT", "AI", "CS", "BPS", "GEN", "BDA", "MSc AI", "BBA A", "BBA B"]
_ROOM_RE = re.compile(r"^(?:LR[- ]?\d{1,2}|LAB[- ]?\d|BDA[- ]?(?:LAB|ALB)|AUDI)$", re.I)
_SEM_RE = re.compile(r"^SEM-(1|3|5|7)$", re.I)
_TIME_RE = re.compile(r"^\d{2}\.\d{2}$")


def _canonical_room(label, venue_names):
    token = re.sub(r"[^A-Z0-9]", "", label.upper())
    if token == "LR37":  # This timetable has a recurring LR-3 typo.
        token = "LR3"
    if token.startswith("LR") and token[2:].isdigit():
        token = "LR" + token[2:]
    elif token.startswith("LAB") and token[3:].isdigit():
        token = "LAB" + token[3:]
    elif token in ("BDALAB", "BDAALB"):
        token = "BDALAB"
    elif token == "AUDI":
        token = "XICAAUDI"
    canonical = {re.sub(r"[^A-Z0-9]", "", name.upper()): name for name in venue_names}
    return canonical.get(token)


def _time_label(value):
    hours, minutes = value.split(".")
    return "{}:{}".format(int(hours), minutes)


def extract_college_timetable(file_object, venue_names):
    """Return Friday timetable rows from the college's grid-style PDF."""
    with pdfplumber.open(file_object) as document:
        if not document.pages:
            raise ValueError("The PDF has no pages.")
        page = document.pages[0]
        words = page.extract_words(x_tolerance=1, y_tolerance=1)

    day = next((day for day in DAYS if any(w["text"].strip(".,:").upper() == day.upper() for w in words)), None)
    if not day:
        raise ValueError("I couldn’t find a weekday heading in this timetable PDF.")

    time_words = sorted((w for w in words if w["x0"] < 140 and _TIME_RE.fullmatch(w["text"])), key=lambda w: w["top"])
    if len(time_words) != len(SLOTS) * 2:
        raise ValueError("I couldn’t identify all timetable period times in this PDF.")
    period_labels = ["{}-{}".format(_time_label(time_words[i]["text"]), _time_label(time_words[i + 1]["text"]))
                     for i in range(0, len(time_words), 2)]
    if period_labels != SLOTS:
        raise ValueError("The PDF period times don’t match the configured college timetable periods.")

    sem_words = sorted((w for w in words if w["x0"] < 160 and _SEM_RE.fullmatch(w["text"].strip())), key=lambda w: w["top"])
    first_year_rows = [w for w in sem_words if w["text"].upper() == "SEM-1"]
    if len(first_year_rows) != len(SLOTS) or len(sem_words) != len(SLOTS) * 4:
        raise ValueError("I couldn’t identify all semester rows in this timetable PDF.")

    # The PDF repeats SEM-1/3/5/7 once per time period. Their y positions
    # anchor the four subrows even where the schedule is split across pages.
    row_groups = []
    for period_index, first_row in enumerate(first_year_rows):
        anchor = first_row["top"]
        group = [w for w in sem_words if anchor - 2 <= w["top"] <= anchor + 55]
        if len(group) != 4:
            raise ValueError("A timetable period is missing one or more semester labels.")
        row_groups.append((anchor, sorted(group, key=lambda w: w["top"]), period_index))

    cells = {}
    for word in words:
        if not 158 <= word["x0"] <= 432:
            continue
        center_x = (word["x0"] + word["x1"]) / 2
        course_index = min(range(len(_COLUMN_CENTERS)), key=lambda i: abs(_COLUMN_CENTERS[i] - center_x))
        if abs(_COLUMN_CENTERS[course_index] - center_x) > 12:
            continue
        period = next((entry for entry in row_groups if entry[0] - 8 <= word["top"] <= entry[0] + 58), None)
        if not period:
            continue
        _, semester_rows, period_index = period
        sem_index = min(range(4), key=lambda i: abs(semester_rows[i]["top"] - word["top"]))
        if abs(semester_rows[sem_index]["top"] - word["top"]) > 9:
            continue
        key = (period_index, semester_rows[sem_index]["text"].upper(), course_index)
        cells.setdefault(key, []).append(word)

    imported = {}
    for (period_index, semester, course_index), cell_words in cells.items():
        room_word = next((w for w in cell_words if _ROOM_RE.fullmatch(w["text"].strip(".,;:").upper())), None)
        if not room_word:
            continue
        venue = _canonical_room(room_word["text"].strip(".,;:"), venue_names)
        if not venue:
            continue
        lines = []
        for word in sorted(cell_words, key=lambda w: (w["top"], w["x0"])):
            if word is room_word or _ROOM_RE.fullmatch(word["text"].strip(".,;:").upper()):
                continue
            if not lines or abs(lines[-1][0] - word["top"]) > 1.3:
                lines.append([word["top"], [word["text"]]])
            else:
                lines[-1][1].append(word["text"])
        subject = " ".join(lines[0][1]).strip() if lines else "Class"
        subject = subject[:60]
        lecture = "{} · {} · {}".format(subject, _COURSES[course_index], semester)
        key = (venue, day, SLOTS[period_index])
        imported.setdefault(key, [])
        if lecture not in imported[key]:
            imported[key].append(lecture)

    rows = [{"venue": venue, "day": row_day, "slot": slot, "lecture": " / ".join(labels)[:100]}
            for (venue, row_day, slot), labels in imported.items()]
    if not rows:
        raise ValueError("No venue entries were recognized. Check that this is the college timetable PDF.")
    return rows
