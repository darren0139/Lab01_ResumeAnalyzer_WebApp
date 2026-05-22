"""
app.py — Streamlit web version of the Resume Analyzer.

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from typing import Any
from pathlib import Path
import streamlit as st


# ---------------------------------------------------------------------------
# Streamlit Cloud secrets -> environment variables
# ---------------------------------------------------------------------------
# llm.py reads environment variables when it is imported.
# Therefore, copy st.secrets into os.environ BEFORE importing analyzer.py / llm.py.
try:
    for key in (
        "MODEL",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OLLAMA_API_BASE",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ):
        if key in st.secrets and key not in os.environ:
            os.environ[key] = str(st.secrets[key])

    # Some Gemini/LiteLLM setups expect GOOGLE_API_KEY instead of GEMINI_API_KEY.
    if "GEMINI_API_KEY" in st.secrets and "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = str(st.secrets["GEMINI_API_KEY"])

except Exception:
    # Local development without Streamlit secrets is fine.
    # llm.py can still read your local .env through python-dotenv.
    pass


from parse import read_resume_pdf, _MIN_JD_CHARS
from analyzer import (
    extract_resume_profile,
    extract_jd_profile,
    analyse_keyword_match,
    analyse_bullets,
    analyse_jargon,
    analyse_structure,
    analyse_degree_alignment,
    summarise_overall,
    compute_overall_score,
)

from report import render_markdown


VALID_DEGREES = ["RTIS", "IMGD", "UXGD", "BFA"]
ATS_PASS_THRESHOLD = 60


def create_markdown_report(report: dict) -> tuple[str, str]:
    """
    Create a Markdown report using the existing report.py renderer.

    Returns:
        markdown_text: The report content as text.
        filename: Suggested filename for download.
    """
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"match_report_{timestamp}.md"
    md_path = output_dir / filename

    render_markdown(report, out_path=md_path)

    markdown_text = md_path.read_text(encoding="utf-8")

    return markdown_text, filename


def validate_jd_text(jd_text: str) -> str:
    """
    Validate JD text pasted into the Streamlit text_area.

    The CLI version used read_jd_text(path).
    The web version does not need a JD .txt file path because the user pastes
    the JD directly into the browser.
    """
    cleaned = jd_text.strip()

    if len(cleaned) < _MIN_JD_CHARS:
        raise ValueError(
            f"Job description text is too short ({len(cleaned)} chars). "
            f"Expected at least {_MIN_JD_CHARS} chars. "
            "Paste the full job description before analysing."
        )

    return cleaned


def read_uploaded_resume_pdf(uploaded_file: Any) -> str:
    """
    Convert Streamlit's uploaded PDF into a temporary file path, then reuse
    the existing read_resume_pdf(path) function.

    This avoids modifying parse.py.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_path = tmp_file.name

    try:
        return read_resume_pdf(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def run_resume_analysis(resume_text: str, jd_text: str, degree: str) -> dict:
    """
    Run the same pipeline as main.py, but show progress in the Streamlit page.
    """

    progress = st.progress(0)
    log = st.container()

    log.write("[1/8] Reading résumé and job description...")
    progress.progress(12)

    log.write("[2/8] Extracting résumé profile...")
    resume_profile = extract_resume_profile(resume_text)
    progress.progress(25)

    log.write("[3/8] Extracting JD profile...")
    jd_profile = extract_jd_profile(jd_text)
    progress.progress(37)

    log.write("[4/8] Analysing keyword match...")
    keyword_match = analyse_keyword_match(resume_profile, jd_profile)
    progress.progress(50)

    log.write("[5/8] Analysing bullet quality...")
    bullets = analyse_bullets(resume_profile)
    progress.progress(62)

    log.write("[6/8] Auditing jargon...")
    jargon = analyse_jargon(resume_profile, degree, jd_profile)
    progress.progress(75)

    log.write("[7/8] Auditing résumé structure...")
    structure = analyse_structure(resume_text)
    progress.progress(87)

    log.write("[8/8] Analysing degree alignment...")
    degree_alignment = analyse_degree_alignment(jd_profile, degree)
    progress.progress(95)

    report = {
        "meta": {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "model": os.getenv("MODEL", "openai/gpt-4o-mini"),
            "degree": degree,
            "ats_pass_threshold": ATS_PASS_THRESHOLD,
        },
        "resume_profile": resume_profile,
        "jd_profile": jd_profile,
        "keyword_match": keyword_match,
        "bullets": bullets,
        "jargon": jargon,
        "structure": structure,
        "degree_alignment": degree_alignment,
    }

    log.write("[Final] Computing overall score and summary...")
    overall_score = compute_overall_score(report)
    report["overall_score"] = overall_score
    report["passes_ats_threshold"] = overall_score >= ATS_PASS_THRESHOLD
    report["summary"] = summarise_overall(report)

    progress.progress(100)

    return report



def score_label(score: int) -> str:
    """Return PASS/FAIL label for the ATS threshold."""
    if score >= ATS_PASS_THRESHOLD:
        return f"PASS — above {ATS_PASS_THRESHOLD}% ATS threshold"
    return f"FAIL — below {ATS_PASS_THRESHOLD}% ATS threshold"


st.set_page_config(
    page_title="Resume × JD Analyzer",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Resume × JD Analyzer")
st.caption("Streamlit web version of the Day 4 CLI Resume Analyzer")

with st.sidebar:
    st.header("Settings")

    degree = st.selectbox(
        "Degree programme",
        VALID_DEGREES,
        index=VALID_DEGREES.index("RTIS"),
        help="Used for the degree-alignment score.",
    )

    model_name = os.getenv("MODEL", "openai/gpt-4o-mini")
    st.write("**Model route:**")
    st.code(model_name)

    st.divider()
    st.write("**How to use**")
    st.write("1. Upload a PDF résumé.")
    st.write("2. Paste the target job description.")
    st.write("3. Click **Analyze Resume**.")

uploaded_resume = st.file_uploader(
    "Upload résumé PDF",
    type=["pdf"],
    help="Upload a text-based PDF résumé. Scanned/image-only PDFs may fail parsing.",
)

jd_text_input = st.text_area(
    "Paste job description",
    height=260,
    placeholder=(
        "Paste the full job description here, including responsibilities, "
        "requirements, tools, technologies, and soft skills..."
    ),
)

analyze_clicked = st.button("Analyze Resume", type="primary", width="stretch")

if analyze_clicked:
    if uploaded_resume is None:
        st.error("Please upload a résumé PDF first.")
        st.stop()

    if not jd_text_input.strip():
        st.error("Please paste a job description first.")
        st.stop()

    try:
        with st.status("Reading résumé PDF...", expanded=True) as status:
            resume_text = read_uploaded_resume_pdf(uploaded_resume)
            st.write(f"Extracted {len(resume_text)} characters from résumé PDF.")

            jd_text = validate_jd_text(jd_text_input)
            st.write(f"Read {len(jd_text)} characters from job description.")

            status.update(label="Running AI analysis...", state="running")
            report = run_resume_analysis(resume_text, jd_text, degree)

            status.update(label="Analysis complete.", state="complete")

        st.session_state["latest_report"] = report

    except ValueError as exc:
        st.error(f"Input error: {exc}")
        st.stop()

    except RuntimeError as exc:
        st.error(f"LLM/API error: {exc}")
        st.info("Check your .env file locally, or Streamlit Cloud secrets after deployment.")
        st.stop()

    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        st.stop()


report = st.session_state.get("latest_report")

if report:
    overall_score = int(report.get("overall_score", 0))
    passed = bool(report.get("passes_ats_threshold", False))

    st.divider()
    st.header("Results")

    if passed:
        st.success(f"Score: {overall_score}/100 ({score_label(overall_score)})")
    else:
        st.error(f"Score: {overall_score}/100 ({score_label(overall_score)})")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Keyword Match", report.get("keyword_match", {}).get("keyword_match_score", 0))
    col2.metric("Bullet Quality", report.get("bullets", {}).get("bullet_quality_avg", 0))
    col3.metric("Structure", report.get("structure", {}).get("structure_score", 0))
    col4.metric("Jargon", report.get("jargon", {}).get("jargon_score", 0))
    col5.metric("Degree Fit", report.get("degree_alignment", {}).get("degree_alignment_score", 0))

    st.subheader("Executive Summary")
    st.markdown(report.get("summary", "_No summary returned._"))

    tab_keywords, tab_bullets, tab_structure, tab_jargon, tab_degree, tab_raw = st.tabs(
        ["Keywords", "Bullets", "Structure", "Jargon", "Degree Fit", "Raw JSON"]
    )

    with tab_keywords:
        st.write("### Present Keywords")
        present = report.get("keyword_match", {}).get("present", [])
        if present:
            st.dataframe(present, use_container_width=True)
        else:
            st.info("No present keywords returned.")

        st.write("### Missing Keywords")
        missing = report.get("keyword_match", {}).get("missing", [])
        if missing:
            st.dataframe(missing, use_container_width=True)
        else:
            st.success("No missing keywords returned.")

    with tab_bullets:
        st.write("### Bullet Quality Audit")
        bullet_rows = report.get("bullets", {}).get("bullets", [])
        if bullet_rows:
            st.dataframe(bullet_rows, use_container_width=True)
        else:
            st.info("No bullet audit rows returned.")

    with tab_structure:
        st.write("### Three-Thirds / ATS Structure")
        st.json(report.get("structure", {}))

    with tab_jargon:
        st.write("### Jargon Flags")
        flags = report.get("jargon", {}).get("flags", [])
        if flags:
            st.dataframe(flags, use_container_width=True)
        else:
            st.success("No jargon flags returned.")

    with tab_degree:
        st.write("### Degree Alignment")
        st.json(report.get("degree_alignment", {}))

    with tab_raw:
        st.write("### Full Report JSON")
        st.json(report)

    st.subheader("Download Reports")
    
    json_bytes = json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8")
    markdown_text, markdown_filename = create_markdown_report(report)

    download_col1, download_col2 = st.columns(2)

    with download_col1:
        st.download_button(
            "Download JSON Report",
            data=json_bytes,
            file_name=f"match_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )

    with download_col2:
        st.download_button(
            "Download Markdown Report",
            data=markdown_text,
            file_name=markdown_filename,
            mime="text/markdown",
            use_container_width=True,
        )

else:
    st.info("Upload a résumé, paste a job description, then click **Analyze Resume**.")
