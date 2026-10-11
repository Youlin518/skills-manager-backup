"""测试完整处理管道"""
import subprocess
import json
import sys
import os

ENCODING = 'utf-8'

def run_with_stdin(script_path, input_str, extra_args=None):
    """Run a Python script with UTF-8 stdin data."""
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    cmd = ['python', '-X', 'utf8', script_path]
    if extra_args:
        cmd.extend(extra_args)
    r = subprocess.run(cmd, input=input_str, capture_output=True, encoding=ENCODING, env=env)
    if r.returncode != 0:
        print(f"ERROR ({script_path}): {r.stderr}")
        return None
    if not r.stdout.strip():
        print(f"EMPTY OUTPUT ({script_path})")
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as e:
        print(f"JSON ERROR ({script_path}): {e}")
        print(f"  Raw: {r.stdout[:300]}")
        return None


# Step 1: Parse test file
print("=== PARSE DATA ===")
cmd1 = ['python', '-X', 'utf8',
        '.claude/skills/building-energy-analysis/scripts/parse_data.py',
        '.claude/skills/building-energy-analysis/evals/test_input.txt']
r1 = subprocess.run(cmd1, capture_output=True, encoding=ENCODING)
if r1.returncode != 0 or not r1.stdout.strip():
    print(f"PARSE ERROR: {r1.stderr}")
    sys.exit(1)
parsed = json.loads(r1.stdout)

bi = parsed.get('building_info', {})
print(f"Building: {bi.get('name', 'N/A')}, Area: {bi.get('area', 0):.0f} m2")
print(f"Type: {bi.get('type', 'N/A')}, Location: {bi.get('location', 'N/A')}")
ed = parsed.get('energy_data', [])
print(f"Records: {len(ed)}, Months: {[r.get('month') for r in ed[:3]]}...")
parsed_json = json.dumps(parsed, ensure_ascii=False)
print()

# Step 2: Energy analysis
print("=== ENERGY ANALYSIS ===")
en = run_with_stdin(
    '.claude/skills/building-energy-analysis/scripts/energy_analysis.py',
    parsed_json)
if en is None:
    sys.exit(1)

ep = en.get('energy_proportion', {})
print(f"Total standard coal: {ep.get('total_coal_kgce', 0):,.1f} kgce")
for p in ep.get('proportions', []):
    print(f"  {p['label']}: {p['coal_equiv_kgce']:,.1f} kgce ({p['proportion_pct']}%)")

mt = en.get('monthly_trend', {})
pk = mt.get('peak_month', {})
vl = mt.get('valley_month', {})
print(f"Peak: Month {pk.get('month')} ({pk.get('total_coal_kgce', 0):,.0f} kgce)")
print(f"Valley: Month {vl.get('month')} ({vl.get('total_coal_kgce', 0):,.0f} kgce)")

ui = en.get('unit_area_intensity', {})
if not ui.get('error'):
    print(f"Intensity: {ui.get('total_coal_per_m2', 0):.2f} kgce/m2.a")
print()

# Step 3: Carbon calculation
print("=== CARBON CALCULATION ===")
ce = run_with_stdin(
    '.claude/skills/building-energy-analysis/scripts/carbon_calculation.py',
    parsed_json, extra_args=['上海', '商业'])
if ce is None:
    sys.exit(1)

print(f"Region: {ce.get('region', 'N/A')} (factor: {ce.get('grid_factor_used', 0)})")
print(f"Total CO2: {ce.get('total_emission_tons', 0):,.2f} t")
for k, v in ce.get('emission_breakdown', {}).items():
    print(f"  {k}: {v.get('co2_tons', 0):,.2f} t ({v.get('pct', 0)}%)")

sc = ce.get('standard_comparison', {})
print(f"\nStandard: {sc.get('icon', '')} {sc.get('level', 'N/A')}")
print(f"  {sc.get('actual_value', 0):.2f} vs Constraint: {sc.get('constraint_value', 0)} vs Guide: {sc.get('guide_value', 0)}")
print(f"  {sc.get('message', '')}")
print()

print("=== ALL TESTS PASSED ===")
