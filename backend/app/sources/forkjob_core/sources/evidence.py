"""Employer ATS evidence shared only where the public field semantics agree."""

from ..models import Job, WorkMode
from ..normalize import format_salary, html_to_text
from ..rich_text import enrich


def labels(value):
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        values = [labels(v) for v in value]
        return ", ".join(dict.fromkeys(v for v in values if v)) or None
    if isinstance(value, dict):
        return labels(value.get("label") or value.get("name"))
    return None


def ats_job(entry, **kwargs):
    """Keep explicit optional ATS facts without adding canonical columns."""
    categories = entry.get("categories") if isinstance(entry.get("categories"), dict) else {}
    salary = entry.get("salaryRange")
    if isinstance(salary, dict):  # Lever's documented currency/interval/min/max
        kwargs["salary"] = format_salary(
            salary.get("min"), salary.get("max"), salary.get("currency"),
            suffix="/" + salary["interval"] if isinstance(salary.get("interval"), str) else "",
        )
    compensation = entry.get("compensation")
    if isinstance(compensation, dict) and isinstance(compensation.get("compensationTierSummary"), str):
        kwargs["salary"] = compensation.get("scrapeableCompensationSalarySummary") or compensation["compensationTierSummary"]
    facts = {
        "Source authority": "employer",
        "Posting language": labels(entry.get("language")),
        "Application URL": entry.get("applyUrl") or entry.get("application_url") or entry.get("apply_url"),
        "Requisition ID": entry.get("requisition_id") or entry.get("requisitionId") or entry.get("reference"),
        "Company URL": entry.get("company_url"),
        "Employment type": labels(entry.get("employmentType") or entry.get("employment_type") or entry.get("typeOfEmployment") or categories.get("commitment")),
        "Technologies": labels(entry.get("tags") or entry.get("skills")),
        "Industry": labels(entry.get("industry")),
        "Job function": labels(entry.get("function")),
        "Workplace type": entry.get("workplaceType"),
        "Application deadline": entry.get("application_deadline"),
        "Expiry": entry.get("validThrough"),
        "Updated date": entry.get("updated_at") or entry.get("updatedAt"),
        "Remote scope": kwargs.get("location") if kwargs.get("work_mode") is WorkMode.REMOTE else None,
        "Locations": labels(categories.get("allLocations")),
    }
    metadata_labels = {"working language": "Language", "visa sponsorship": "Visa sponsorship", "relocation": "Relocation", "remote scope": "Remote scope", "skills": "Technologies", "seniority": "Experience level", "salary": "Salary"}
    for item in entry.get("metadata") or []:
        if not isinstance(item, dict):
            continue
        label = metadata_labels.get(str(item.get("name") or "").strip().lower())
        if not label:
            continue
        value = item.get("value")
        if isinstance(value, bool) and label in {"Visa sponsorship", "Relocation"}:
            value = "Yes" if value else "No"
        else:
            value = labels(value)
        if value:
            facts[label] = value
    if not kwargs.get("language"):
        kwargs["language"] = facts.get("Language")
    if not kwargs.get("salary"):
        kwargs["salary"] = facts.get("Salary")
    for key, label in (("visaSponsorship", "Visa sponsorship"), ("relocation", "Relocation")):
        if isinstance(entry.get(key), bool):
            facts[label] = "Yes" if entry[key] else "No"
    prose = kwargs.get("description")
    # The public payload may contain additional job-specific prose sections.
    for key in ("requirements", "benefits", "additional", "additionalPlain", "jobAd"):
        value = entry.get(key)
        if isinstance(value, str):
            text = html_to_text(value)
            if text and text not in (prose or ""):
                prose = "\n\n".join(v for v in (prose, text) if v)
        elif key == "jobAd" and isinstance(value, dict):
            sections = value.get("sections") or {}
            for section in sections.values() if isinstance(sections, dict) else []:
                text = html_to_text(section.get("text")) if isinstance(section, dict) else None
                if text and text not in (prose or ""):
                    prose = "\n\n".join(v for v in (prose, text) if v)
    for section in entry.get("lists") or []:
        if isinstance(section, dict):
            text = html_to_text(section.get("content"))
            if text:
                prose = "\n\n".join(v for v in (prose, labels(section.get("text")), text) if v)
    kwargs["description"] = enrich(prose, kwargs["source"], facts)
    return Job.build(**kwargs)
