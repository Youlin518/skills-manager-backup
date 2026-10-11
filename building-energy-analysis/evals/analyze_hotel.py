"""
苏州高铁金科大酒店 — 能耗分析脚本
处理每日抄表数据，按月汇总后运行 skill 的分析管道
"""
import openpyxl
import json
import subprocess
import os
import sys
from collections import defaultdict
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'
ENCODING = 'utf-8'
SCRIPT_DIR = '.claude/skills/building-energy-analysis'

def run_script(script_path, stdin_data=None, extra_args=None):
    """Run a script and return parsed JSON."""
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    if stdin_data:
        r = subprocess.run(['python', '-X', 'utf8', script_path],
                          input=stdin_data, capture_output=True,
                          encoding=ENCODING, errors='replace', env=env)
    else:
        cmd = ['python', '-X', 'utf8', script_path]
        if extra_args:
            cmd.extend(extra_args)
        r = subprocess.run(cmd, capture_output=True,
                          encoding=ENCODING, errors='replace', env=env)
    if r.returncode != 0:
        print(f"Script error ({script_path}): {r.stderr}")
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        print(f"JSON error: {r.stdout[:200]}")
        return None


# ================================================================
# Step 1: Extract daily data from Excel, aggregate by month
# ================================================================
print("=" * 60)
print("  苏州高铁金科大酒店 — 能耗分析报告")
print("=" * 60)

EXCEL_PATH = r'C:\Users\86158\Desktop\苏州高铁金科大酒店节能改造\2025年能源消耗走势.xlsx'
wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
ws = wb['每日抄表发票价格']

# Column mapping from Row 2 (header)
# Col O (15): 水用量
# Col P (16): 电用量 (kWh, already multiplied by 4000)
# Col Q (17): 气用量 (m³)
# Col R (18): 天气/温度
# Col A (1): 日期

COL_WATER = 15   # 水用量
COL_ELEC = 16    # 电用量 (kWh)
COL_GAS = 17     # 气用量 (m³)
COL_WEATHER = 18 # 天气
COL_DATE = 1     # 日期

# Collect daily data starting from row 3
monthly = defaultdict(lambda: {'water': 0, 'elec': 0, 'gas': 0, 'days': 0})
daily_records = []

for row_idx in range(3, ws.max_row + 1):
    date_val = ws.cell(row=row_idx, column=COL_DATE).value
    water = ws.cell(row=row_idx, column=COL_WATER).value
    elec = ws.cell(row=row_idx, column=COL_ELEC).value
    gas = ws.cell(row=row_idx, column=COL_GAS).value

    if date_val is None:
        continue

    # Parse date
    if isinstance(date_val, datetime):
        dt = date_val
    elif isinstance(date_val, str):
        try:
            dt = datetime.strptime(date_val, '%Y-%m-%d %H:%M:%S')
        except:
            continue
    else:
        continue

    month = dt.month
    year = dt.year

    w = float(water) if water is not None else 0
    e = float(elec) if elec is not None else 0
    g = float(gas) if gas is not None else 0

    monthly[month]['water'] += w
    monthly[month]['elec'] += e
    monthly[month]['gas'] += g
    monthly[month]['days'] += 1

    daily_records.append({
        'date': dt.strftime('%Y-%m-%d'),
        'month': month,
        'water': round(w, 1),
        'electricity': round(e, 1),
        'gas': round(g, 1),
    })

# ================================================================
# Step 2: Display extracted data
# ================================================================
print(f"\n  数据概况:")
print(f"  数据范围: {daily_records[0]['date']} ~ {daily_records[-1]['date']}")
print(f"  总天数: {len(daily_records)} 天")
print(f"  覆盖月份: {len(monthly)} 个月")

# Check which months have data
print(f"\n  各月数据天数:")
for m in sorted(monthly.keys()):
    md = monthly[m]
    print(f"    {m:2d}月: {md['days']:3d}天  水:{md['water']:>12,.1f} t  电:{md['elec']:>14,.1f} kWh  气:{md['gas']:>12,.1f} m³")

# ================================================================
# Step 3: Build standardized data for the skill pipeline
# ================================================================
# The hotel uses boiler gas for heating (no district heating)
# Water is not an energy source but we'll include it for reference

print(f"\n{'─'*60}")
print("  Step 3: 运行 Skill 能源分析管道")
print(f"{'─'*60}")

# Convert to the format expected by energy_analysis.py and carbon_calculation.py
energy_data = []
for m in sorted(monthly.keys()):
    md = monthly[m]
    energy_data.append({
        'month': m,
        'electricity_kwh': round(md['elec'], 2),
        'gas_m3': round(md['gas'], 2),
        'heat_gj': 0,  # No district heating
    })

# Total electricity (for annual)
total_elec = sum(r['electricity_kwh'] for r in energy_data)
total_gas = sum(r['gas_m3'] for r in energy_data)

# Standard coal conversion
COAL_ELEC = 0.1229
COAL_GAS = 1.2143
total_coal = total_elec * COAL_ELEC + total_gas * COAL_GAS

print(f"\n  年总用电: {total_elec:,.1f} kWh")
print(f"  年总用气: {total_gas:,.1f} m³")
print(f"  折标煤: {total_coal:,.1f} kgce = {total_coal/1000:,.1f} tce")

# Need building area - ask if not available
# For now, estimate or check if we can find it
# Typical 5-star hotel: guess around 50,000-80,000 m²
# Let me look for area information in the file or directory

# Check directory for any additional info files
import glob
info_dir = r'C:\Users\86158\Desktop\苏州高铁金科大酒店节能改造'
for f in os.listdir(info_dir):
    print(f"  Found in dir: {f}")

# Run the energy analysis
pipe_input = json.dumps({
    'building_info': {
        'name': '苏州高铁金科大酒店',
        'area': 0,  # Unknown - will ask user
        'type': '酒店',
        'location': '江苏苏州',
        'year': 2025,
    },
    'energy_data': energy_data,
}, ensure_ascii=False)

print(f"\n  能源数据 (JSON):")
print(json.dumps(energy_data, ensure_ascii=False, indent=2))
