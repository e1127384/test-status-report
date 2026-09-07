# test-status-report
test-status-report

## Generate executive defect HTML report

This repository includes a Python utility that converts an Excel defect export into a styled HTML status page with KPIs and breakdowns.

### Input columns expected

- defect_id
- story_name
- bug_created_date
- bug_title
- last_updated_date
- last_updated_by
- bug_status
- assigned_to
- priority
- severity

### Usage

```bash
pip install -r /home/runner/work/test-status-report/test-status-report/requirements.txt
python /home/runner/work/test-status-report/test-status-report/generate_defect_report.py defects.xlsx -o defect_report.html --title "Executive Defect Dashboard"
```
