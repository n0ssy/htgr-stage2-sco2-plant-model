#!/usr/bin/env python3
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / 'reports/final/source/UCL-HTGR-Group3-Report-DRAFT.md'
NUMBERS = ROOT / 'reports/final/qa/numbers_lock_table.csv'
OUT = ROOT / 'reports/final/qa/report_sync_check.json'

text = REPORT.read_text(encoding='utf-8')

checks = {}

# 1) Placeholder elimination
placeholder_patterns = [r"\[\?\?\?", r"Appendix \[", r"TODO", r"TBD", r"INSERT_", r"@@@"]
found_placeholders = []
for pat in placeholder_patterns:
    if re.search(pat, text):
        found_placeholders.append(pat)
checks['placeholder_elimination'] = {
    'pass': len(found_placeholders) == 0,
    'found_patterns': found_placeholders,
}

# 2) Headline number presence
required_literals = ['S2_30MW_FUELDISP', 'fuel_displacement', '30.0 MWth', '9.939 MWe', '33.90%', '33.13%', '9,898', '329.9']
missing_literals = [x for x in required_literals if x not in text]
checks['headline_literals'] = {
    'pass': len(missing_literals) == 0,
    'missing': missing_literals,
}

# 3) Boundary consistency
has_op_only = 'operational_only' in text
has_fuel_disp = 'fuel_displacement' in text
checks['boundary_consistency'] = {
    'pass': has_op_only and has_fuel_disp,
    'operational_only_present': has_op_only,
    'fuel_displacement_present': has_fuel_disp,
}

# 4) 36 MWth usage guard (historical/sensitivity only)
count_36 = len(re.findall(r'36 MWth', text))
checks['historical_36mw_guard'] = {
    'pass': count_36 <= 4,
    'count': count_36,
}

# 5) Numbers-lock schema and minimum rows
with NUMBERS.open(newline='') as f:
    r = csv.DictReader(f)
    rows = list(r)
required_cols = ['metric_id','value','units','scenario_id','boundary_mode','source_file','json_path','owner']
missing_cols = [c for c in required_cols if c not in r.fieldnames]
checks['numbers_lock_table'] = {
    'pass': len(missing_cols) == 0 and len(rows) >= 30,
    'row_count': len(rows),
    'missing_columns': missing_cols,
}

# 6) Explicit mention of canonical feasibility in report
checks['canonical_feasibility_statement'] = {
    'pass': ('all four canonical scenarios' in text.lower()) or ('S0_BASE_30MW_OPONLY' in text and 'S3_36MW_FUELDISP' in text),
}

overall = all(item['pass'] for item in checks.values())

payload = {
    'overall_pass': overall,
    'checks': checks,
    'report_path': str(REPORT),
    'numbers_lock_path': str(NUMBERS),
}

OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
print(json.dumps(payload, indent=2))
