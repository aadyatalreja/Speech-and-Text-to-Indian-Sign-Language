import csv

import pytest

from eval.isign_coverage import coverage, load_transcripts, video_split


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["uid", "english"])
        writer.writerows(rows)


def test_segments_from_same_video_stay_together(tmp_path):
    path = tmp_path / "transcripts.csv"
    first = "source-a"
    split = video_split(first)
    other = next(str(i) for i in range(100) if video_split(str(i)) != split)
    write_csv(
        path, [(f"{first}-1", "First, sample"), (f"{other}-1", "Other"), (f"{first}-2", "Second")]
    )
    assert load_transcripts(path, "uid", "english", split) == (["First, sample", "Second"], 1)
    assert load_transcripts(path, "uid", "english", split, limit=1) == (["First, sample"], 1)


def test_coverage_reuses_offline_measurement_without_exposing_sentences(tmp_path):
    path = tmp_path / "transcripts.csv"
    write_csv(path, [("example-1", "HELLO")])

    def measure(sentences):
        assert sentences == ["HELLO"]
        return {
            "sentences": sentences,
            "sentence_count": 1,
            "error_count": 0,
            "total_gloss_tokens": 1,
            "fs_count": 0,
            "fs_rate": 0.0,
            "top_oov_words": [],
        }

    report = coverage(path, "uid", "english", "all", report_builder=measure)
    assert report["distinct_source_videos"] == 1
    assert report["fs_rate"] == 0
    assert "sentences" not in report


def test_duplicate_uid_fails_with_line_number(tmp_path):
    path = tmp_path / "transcripts.csv"
    write_csv(path, [("example-1", "Hello"), ("example-1", "World")])
    with pytest.raises(ValueError, match="Duplicate UID at CSV line 3"):
        load_transcripts(path, "uid", "english", "all")
