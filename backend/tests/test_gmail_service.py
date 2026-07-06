from services.gmail_service import extract_study_id

SUBJECT = "SleepView HST report is ready"
BODY = (
    "Please login to the SleepView web portal. Interpretation reports have "
    "been delivered for the following study. Study ID #0000000000."
)


def test_exact_template_match():
    assert extract_study_id(SUBJECT, BODY) == "0000000000"


def test_html_entities_and_tags_are_normalized():
    html_body = (
        "<p>Please login to the SleepView web portal.&nbsp;Interpretation "
        "reports have been <b>delivered</b> for the following study. "
        "Study&nbsp;ID&nbsp;#1234567890.</p>"
    )
    assert extract_study_id(SUBJECT, html_body) == "1234567890"


def test_extra_whitespace_and_newlines_tolerated():
    noisy_body = (
        "Please  login to the   SleepView web portal.\n\n"
        "Interpretation reports have\nbeen delivered for the following "
        "study.\n\nStudy ID   #9876543210."
    )
    assert extract_study_id(SUBJECT, noisy_body) == "9876543210"


def test_missing_delivered_keyword_is_rejected():
    pending_body = (
        "Please login to the SleepView web portal. Interpretation reports "
        "are pending for the following study. Study ID #0000000000."
    )
    assert extract_study_id(SUBJECT, pending_body) is None


def test_wrong_subject_is_rejected():
    assert extract_study_id("SleepView account notice", BODY) is None


def test_missing_subject_is_rejected_even_with_delivered_elsewhere():
    other_subject = "Your invoice is ready"
    assert extract_study_id(other_subject, BODY) is None


def test_only_labeled_study_id_is_extracted_not_stray_digits():
    body_with_noise = (
        "Please login to the SleepView web portal. Reference: 5551234567. "
        "Interpretation reports have been delivered for the following "
        "study. Study ID #1112223334."
    )
    assert extract_study_id(SUBJECT, body_with_noise) == "1112223334"


def test_subject_match_is_case_insensitive_and_tolerates_prefix():
    assert extract_study_id("Fwd: SLEEPVIEW HST REPORT IS READY", BODY) == "0000000000"
