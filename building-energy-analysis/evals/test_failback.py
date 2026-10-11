"""Test parse failback features"""
import subprocess, json, sys

HOTEL = r'C:\Users\86158\Desktop\苏州高铁金科大酒店节能改造\2025年能源消耗走势.xlsx'

# Test --preview
print("=== --preview ===")
r = subprocess.run(['python', '-X', 'utf8', '.claude/skills/building-energy-analysis/scripts/parse_data.py',
                    '--preview', HOTEL],
                   capture_output=True, text=True, encoding='utf-8')
d = json.loads(r.stdout)
print(f"Sheets: {list(d['sheets'].keys())}")
s = d['sheets']['每日抄表发票价格']
print(f"Total rows: {s['total_rows']}, cols: {s['total_cols']}")
for row in s['preview_rows'][:3]:
    cells_short = dict(list(row['cells'].items())[:8])
    print(f"  Row {row['row']}: {cells_short}")

# Test --columns with daily cumulative mode
print("\n=== --columns P:kWh,Q:m3 --daily ===")
r2 = subprocess.run(['python', '-X', 'utf8', '.claude/skills/building-energy-analysis/scripts/parse_data.py',
                     '--columns', 'P:kWh,Q:m3', '--daily', HOTEL],
                    capture_output=True, text=True, encoding='utf-8')
d2 = json.loads(r2.stdout)
ed = d2.get('energy_data', [])
print(f"Error: {d2.get('error', 'none')}")
print(f"Months: {len(ed)}")
for rec in ed[:3]:
    print(f"  M{rec.get('month','?')}: kWh={rec.get('kWh',0):,.0f} m3={rec.get('m3',0):,.0f}")

total_kwh = sum(r.get('kWh', 0) or 0 for r in ed)
total_m3 = sum(r.get('m3', 0) or 0 for r in ed)
print(f"Total kWh: {total_kwh:,.0f} (expected: 5,766,840)")
print(f"Total m3: {total_m3:,.0f} (expected: 457,353)")
print(f"Match: {'OK' if abs(total_kwh-5766840)<1000 and abs(total_m3-457353)<1000 else 'MISMATCH'}")
