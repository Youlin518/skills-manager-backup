"""端到端测试：--preview → --columns → 分析 → 报告"""
import subprocess, json, sys, os
sys.path.insert(0, '.claude/skills/building-energy-analysis/scripts')
from energy_analysis import calc_energy_proportion, calc_monthly_trend, validate_data
from carbon_calculation import calc_carbon_emission, compare_with_standard
from generate_report import generate_report

HOTEL = r'C:\Users\86158\Desktop\苏州高铁金科大酒店节能改造\2025年能源消耗走势.xlsx'
AREA = 56846  # From user's statistics

# Step 1: Preview
print("=== Step 1: --preview ===")
r = subprocess.run(['python', '-X', 'utf8', '.claude/skills/building-energy-analysis/scripts/parse_data.py',
                    '--preview', HOTEL], capture_output=True, text=True, encoding='utf-8')
preview = json.loads(r.stdout)
print(f"Sheets: {list(preview['sheets'].keys())}")
s = preview['sheets']['每日抄表发票价格']
print(f"Rows: {s['total_rows']}, Cols: {s['total_cols']}")
print(f"User would see Col 16(P)='{s['preview_rows'][1]['cells'].get(16,'?')}', Col 17(Q)='{s['preview_rows'][1]['cells'].get(17,'?')}'")

# Step 2: Parse with columns
print("\n=== Step 2: --columns P:kWh,Q:m3 --daily ===")
r2 = subprocess.run(['python', '-X', 'utf8', '.claude/skills/building-energy-analysis/scripts/parse_data.py',
                     '--columns', 'P:electricity_kwh,Q:gas_m3', '--daily', HOTEL],
                    capture_output=True, text=True, encoding='utf-8')
data = json.loads(r2.stdout)
ed = data.get('energy_data', [])
print(f"Parsed {len(ed)} months, sample: M{ed[0]['month']} elec={ed[0].get('electricity_kwh',0):,.0f} gas={ed[0].get('gas_m3',0):,.0f}")

# Step 3: Validate
print("\n=== Step 3: Data Validation ===")
warnings = validate_data(ed)
if warnings:
    for w in warnings:
        print(f"  [{w['type']}] {w['message']}")
else:
    print("  No warnings - data looks clean")

# Step 4: Energy Analysis
print("\n=== Step 4: Energy Analysis ===")
ep = calc_energy_proportion(ed)
print(f"Total coal: {ep['total_coal_kgce']:,.0f} kgce ({ep['total_coal_kgce']/1000:.1f} tce)")
for p in ep['proportions']:
    if p['amount'] > 0:
        print(f"  {p['label']}: {p['coal_equiv_kgce']:>12,.0f} kgce ({p['proportion_pct']}%)")

mt = calc_monthly_trend(ed)
print(f"Peak: M{mt['peak_month']['month']}, Valley: M{mt['valley_month']['month']}")

# Step 5: Carbon + Standard
print("\n=== Step 5: Carbon + Standard ===")
ce = calc_carbon_emission(ed, '苏州')
coal_per_m2 = ep['total_coal_kgce'] / AREA
carbon_per_m2 = ce['total_emission_tons'] * 1000 / AREA
sc = compare_with_standard(coal_per_m2, carbon_per_m2, '酒店', '苏州',
                           star_rating='五星级', climate_zone='夏热冬冷I区')
print(f"CO2: {ce['total_emission_tons']:,.2f} t (factor: {ce['grid_factor_used']})")
print(f"Coal/m2: {coal_per_m2:.2f} kgce/m2.a")
print(f"Standard: {sc['energy_icon']} {sc['energy_level']} ({sc['standard_source']})")

# Step 6: Generate Report
print("\n=== Step 6: Generate Report ===")
outdir = r'C:\Users\86158\Desktop\苏州高铁金科大酒店节能改造\skill测试\test'
os.makedirs(outdir, exist_ok=True)
combined = {
    'building_info': {'name': '苏州高铁金科大酒店', 'area': AREA, 'type': '酒店',
                       'location': '苏州', 'year': 2025},
    'energy_proportion': ep, 'monthly_trend': mt,
    'unit_area_intensity': {'total_coal_per_m2': coal_per_m2},
    'carbon_emission': ce,
    'carbon_intensity_kgco2_per_m2': round(carbon_per_m2, 2),
    'total_coal_kgce': round(ep['total_coal_kgce'], 2),
    'coal_per_m2_kgce': round(coal_per_m2, 2),
    'standard_comparison': sc,
    'data_notes': ['通过 --columns P:electricity_kwh,Q:gas_m3 --daily 模式解析。'],
}
output = os.path.join(outdir, '酒店_端到端测试报告.docx')
generate_report(combined, output)
print(f"Report: {output}")

# Verify totals match user's reference
total_elec = sum(r.get('electricity_kwh', 0) or 0 for r in ed)
total_gas = sum(r.get('gas_m3', 0) or 0 for r in ed)
print(f"\n=== Verification ===")
print(f"Total elec: {total_elec:,.0f} (ref: 5,766,840) -> {'OK' if abs(total_elec-5766840)<1000 else 'FAIL'}")
print(f"Total gas: {total_gas:,.0f} (ref: 457,353) -> {'OK' if abs(total_gas-457353)<1000 else 'FAIL'}")
print(f"Total coal: {ep['total_coal_kgce']:,.0f} (ref: 2,273,882) -> {'OK' if abs(ep['total_coal_kgce']-2273882)<2000 else 'FAIL'}")
print(f"\nALL DONE")
