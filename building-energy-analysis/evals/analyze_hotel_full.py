"""
苏州高铁金科大酒店 — 完整能耗分析报告
直接调用 skill 的 energy_analysis 和 carbon_calculation 模块
"""
import sys
import os
sys.path.insert(0, '.claude/skills/building-energy-analysis/scripts')

# Import functions directly from the skill scripts
from energy_analysis import calc_energy_proportion, calc_monthly_trend, calc_unit_area_intensity
from carbon_calculation import calc_carbon_emission, calc_carbon_intensity, compare_with_standard

# The extracted monthly data
energy_data = [
    {"month": 1, "electricity_kwh": 400880.0, "gas_m3": 78319.0, "heat_gj": 0},
    {"month": 2, "electricity_kwh": 341000.0, "gas_m3": 70161.0, "heat_gj": 0},
    {"month": 3, "electricity_kwh": 357520.0, "gas_m3": 48102.0, "heat_gj": 0},
    {"month": 4, "electricity_kwh": 365240.0, "gas_m3": 30740.0, "heat_gj": 0},
    {"month": 5, "electricity_kwh": 449720.0, "gas_m3": 26344.0, "heat_gj": 0},
    {"month": 6, "electricity_kwh": 500200.0, "gas_m3": 21914.0, "heat_gj": 0},
    {"month": 7, "electricity_kwh": 655360.0, "gas_m3": 19144.0, "heat_gj": 0},
    {"month": 8, "electricity_kwh": 685760.0, "gas_m3": 20701.0, "heat_gj": 0},
    {"month": 9, "electricity_kwh": 632240.0, "gas_m3": 22114.0, "heat_gj": 0},
    {"month": 10, "electricity_kwh": 509400.0, "gas_m3": 24700.0, "heat_gj": 0},
    {"month": 11, "electricity_kwh": 420240.0, "gas_m3": 37943.0, "heat_gj": 0},
    {"month": 12, "electricity_kwh": 449280.0, "gas_m3": 57171.0, "heat_gj": 0},
]

PROVINCE = "江苏苏州"
BUILDING_TYPE = "酒店"
BUILDING_NAME = "苏州高铁金科大酒店"

print("=" * 65)
print(f"  {BUILDING_NAME} — 2025年能耗分析报告")
print("=" * 65)

# ================================================================
# 1. Energy Proportion Analysis
# ================================================================
print("\n" + "─" * 50)
print("  一、能源比例分析")
print("─" * 50)

ep = calc_energy_proportion(energy_data)
total_coal = ep['total_coal_kgce']
print(f"\n  年总标煤量: {total_coal:,.0f} kgce = {total_coal/1000:,.1f} tce\n")
print(f"  {'能源类型':<8s} {'实物量':>14s} {'折标煤(kgce)':>16s} {'占比':>8s}")
print(f"  {'-'*48}")
for p in ep['proportions']:
    if p['amount'] > 0:
        print(f"  {p['label']:<8s} {p['amount']:>12,.0f} {p['unit']:<4s} {p['coal_equiv_kgce']:>16,.0f} {p['proportion_pct']:>7.1f}%")
print(f"  {'-'*48}")
print(f"  {'合计':<8s} {'':>14s} {total_coal:>16,.0f} {'100.0%':>8s}")

# ================================================================
# 2. Monthly Trend Analysis
# ================================================================
print("\n" + "─" * 50)
print("  二、逐月用能量分析")
print("─" * 50)

mt = calc_monthly_trend(energy_data)
print(f"\n  年总能耗: {mt['total_annual_coal_kgce']:,.0f} kgce")
print(f"  月均能耗: {mt['monthly_avg_coal_kgce']:,.0f} kgce")

peak = mt['peak_month']
valley = mt['valley_month']
print(f"\n  峰值月: {peak['month']}月 ({peak['total_coal_kgce']:,.0f} kgce) — {peak['total_coal_kgce']/mt['monthly_avg_coal_kgce']:.1f}x 均值")
print(f"  谷值月: {valley['month']}月 ({valley['total_coal_kgce']:,.0f} kgce) — {valley['total_coal_kgce']/mt['monthly_avg_coal_kgce']:.1f}x 均值")
print(f"  峰谷比: {peak['total_coal_kgce']/valley['total_coal_kgce']:.2f}")

print(f"\n  逐月能耗明细:")
print(f"  {'月份':<6s} {'电力(kWh)':>12s} {'天然气(m³)':>12s} {'折标煤(kgce)':>15s} {'占比':>8s}")
print(f"  {'-'*55}")
for m in mt['monthly_data']:
    pct = m['total_coal_kgce'] / mt['total_annual_coal_kgce'] * 100 if mt['total_annual_coal_kgce'] > 0 else 0
    print(f"  {m['month']:>2d}月   {m['electricity_kwh']:>12,.0f} {m['gas_m3']:>12,.0f} {m['total_coal_kgce']:>15,.0f} {pct:>7.1f}%")

# Seasonal analysis
sa = mt.get('seasonal_analysis', {})
if sa.get('season_data'):
    print(f"\n  季节分布:")
    for sname, sdata in sa['season_data'].items():
        bar = '█' * int(sdata.get('pct_of_annual', 0) / 2)
        print(f"  {sname:<12s}: 均值 {sdata['avg_coal_kgce']:>10,.0f} kgce  ({sdata.get('pct_of_annual', 0):.1f}%) {bar}")
    if sa.get('dominant_season'):
        print(f"  主导季节: {sa['dominant_season']}")

# ================================================================
# 3. Carbon Emission Calculation
# ================================================================
print("\n" + "─" * 50)
print("  三、碳排放指标计算")
print("─" * 50)

ce = calc_carbon_emission(energy_data, PROVINCE)
print(f"\n  区域电网: {ce['region']} (排放因子: {ce['grid_factor_used']} kgCO₂/kWh)")
print(f"\n  {'排放源':<10s} {'消耗量':>14s} {'排放因子':>14s} {'碳排放(tCO₂)':>15s} {'占比':>8s}")
print(f"  {'-'*63}")
for key, val in ce['emission_breakdown'].items():
    if val['co2_tons'] > 0.1:
        print(f"  {key:<10s} {val['amount']:>12,.0f} {val['unit']:<4s} {val['factor']:>10.4f} {val['factor_unit']:<10s} {val['co2_tons']:>15,.2f} {val['pct']:>7.1f}%")
print(f"  {'-'*63}")
print(f"  {'合计':<10s} {'':>14s} {'':>14s} {ce['total_emission_tons']:>15,.2f} {'100.0%':>8s}")

# ================================================================
# 4. Standard Comparison
# ================================================================
print("\n" + "─" * 50)
print("  四、地方政策碳排放标准对标")
print("─" * 50)

sc = compare_with_standard(total_coal / 1, BUILDING_TYPE, PROVINCE)  # Using 1 m2 as dummy area since we don't have area
print(f"\n  注意: 缺少建筑面积数据，无法计算单位面积能耗强度进行标准对标。")
print(f"  以下为参考对标（需提供建筑面积后更新）:")

# Calculate per-area values for different possible areas
print(f"\n  按不同建筑面积的能耗强度估算:")
for area in [30000, 45000, 60000, 75000, 90000]:
    coal_per_m2 = total_coal / area
    sc = compare_with_standard(coal_per_m2, BUILDING_TYPE, PROVINCE)
    if sc['status'] == 'matched':
        print(f"    假设面积 {area:,d} m² → 能耗强度 {coal_per_m2:.2f} kgce/m²·a → {sc['icon']} {sc['level']} (约束值: {sc['constraint_value']}, 引导值: {sc['guide_value']})")

# ================================================================
# 5. Summary & Recommendations
# ================================================================
print("\n" + "─" * 50)
print("  五、分析结论与节能建议")
print("─" * 50)

print(f"""
  1. 能源结构: 电力占比 {ep['proportions'][0]['proportion_pct']}%，天然气占比 {ep['proportions'][1]['proportion_pct']}%，
     无市政热力。该酒店采用燃气锅炉自采暖模式。

  2. 用电特征: 夏季(7-8月)为用电高峰，月均 {685760/31:,.0f} kWh/天，
     冬季(12-2月)次之，反映制冷和采暖两季的电力需求。

  3. 用气特征: 冬季(12-2月)为用气高峰，主要用于采暖；
     夏季(6-9月)用气量最低，仅用于厨房和热水。

  4. 碳排放: 年总排放 {ce['total_emission_tons']:,.0f} tCO₂，
     其中电力排放占 {ce['emission_breakdown']['electricity']['pct']}%，天然气排放占 {ce['emission_breakdown']['gas']['pct']}%。

  5. 季节特征: 能耗呈现"冬夏双峰"特征——
     冬季(12-2月)以采暖用气为主，
     夏季(7-8月)以制冷冷用电为主。

  💡 节能建议:
  • 天然气费用占比高，建议评估热泵替代燃气锅炉的可行性
  • 夏季制冷系统可优化运行策略（如冰蓄冷、变频改造）
  • 关注过渡季(4月/10月)的免费供冷机会
""")

print("=" * 65)
print("  报告完毕。请提供建筑面积以完善单位面积指标和对标分析。")
print("=" * 65)
