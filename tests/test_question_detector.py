"""Question detection: pure rules, no model and no HTTP."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.domain.qa.detector import is_question, merge_continuations


def test_question_mark_wins() -> None:
    assert is_question("Hôm nay trời đẹp không?")
    assert is_question("  ?  ")


def test_leading_markers() -> None:
    for text in (
        "Ai là chủ tịch nước Việt Nam",
        "Gì đây",
        "Bao nhiêu tuổi",
        "Ở đâu có bán",
        "Tại sao lại như vậy",
        "Cho tôi biết quy trình đăng ký",
        "Xin hỏi giờ làm việc",
        "What is the capital of Vietnam",
    ):
        assert is_question(text), text


def test_markers_inside_the_sentence() -> None:
    assert is_question("Quy trình gồm mấy bước nào")
    assert is_question("Thủ đô Việt Nam là gì")
    assert is_question("Hồ sơ cần những giấy tờ gì")
    assert is_question("Làm thủ tục ở đâu")


def test_noisy_dictation_is_not_a_question() -> None:
    noise = (
        "trước nay xếp hàng da sổ thông qua vâng đấy là đóng cái sau là đóng sau "
        "tôi mới mang lại nhà vất vả bên kia nó mai được phép mai một ngày đó nó "
        "mới xong rồi không khí lạnh hôm qua sáng chắc anh mới đi tìm gian khó"
    )
    assert not is_question(noise)


def test_trailing_particles() -> None:
    assert is_question("Bạn khỏe không")
    assert is_question("Bạn ăn cơm chưa")
    assert is_question("Đúng rồi nhỉ")


def test_statements_are_not_questions() -> None:
    for text in (
        "Hôm nay trời đẹp",
        "Tôi muốn đăng ký dịch vụ",
        "Cảm ơn bạn",
        "",
        "   ",
        "...",
    ):
        assert not is_question(text), text


def test_merge_continuations_same_question() -> None:
    parts = [("Quy trình đăng ký", 10.0), ("gồm những bước nào", 10.6)]
    assert merge_continuations(parts) == "Quy trình đăng ký gồm những bước nào"


def test_merge_continuations_breaks_on_long_pause() -> None:
    parts = [("Xin chào", 10.0), ("Bao nhiêu tuổi", 12.0)]
    assert merge_continuations(parts, max_gap=1.2) == "Bao nhiêu tuổi"


def test_merge_continuations_ignores_empty_parts() -> None:
    parts = [("Câu hỏi", 1.0), ("", 1.2), ("tiếp theo", 1.4)]
    assert merge_continuations(parts) == "Câu hỏi tiếp theo"
    assert merge_continuations([]) == ""
