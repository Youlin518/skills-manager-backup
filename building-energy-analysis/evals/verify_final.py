"""苏州高铁金科大酒店 — 最终验证"""
import sys
sys.path.insert(0, '.claude/skills/building-energy-analysis/scripts')
from carbon_calculation import *
from energy_analysis import calc_energy_proportion, calc_monthly_trend

SEP = "=" * 60

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

AREA = 56846
USER_REF = {
    'total_coal': 2273882.07, 'elec_coal': 1718518.32, 'gas_coal': 555363.75,
    'coal_per_m2': 40.00, 'total_co2_kg': 4343828.83, 'carbon_per_m2': 76.41,
}

print(SEP)
print("  苏州高铁金科大酒店 — 最终验证")
print("  五星级 | 夏热冬冷I区 | 56,846 m2")
print(SEP)

# [1] Energy Analysis
ep = calc_energy_proportion(energy_data)
total_coal = ep['total_coal_kgce']
coal_per_m2 = total_coal / AREA

print("\n[1] 能源比例分析")
print(f"  总标煤: {total_coal:,.1f} kgce (用户: {USER_REF['total_coal']:,.1f})")
print(f"  差异: {abs(total_coal-USER_REF['total_coal'])/USER_REF['total_coal']*100:.2f}%")
for p in ep['proportions']:
    user_v = USER_REF['elec_coal'] if p['label'] == '电力' else USER_REF['gas_coal']
    print(f"  {p['label']}: {p['coal_equiv_kgce']:>12,.1f} kgce ({p['proportion_pct']}%)  用户: {user_v:,.1f}")
print(f"  单位面积: {coal_per_m2:.2f} kgce/m2 (用户: {USER_REF['coal_per_m2']:.2f})")

# [2] Carbon
ce = calc_carbon_emission(energy_data, '苏州')
carbon_per_m2 = ce['total_emission_tons'] * 1000 / AREA
user_co2_t = USER_REF['total_co2_kg'] / 1000
print(f"\n[2] 碳排放计算")
print(f"  区域: {ce['region']} (因子: {ce['grid_factor_used']})")
print(f"  总排放: {ce['total_emission_tons']:,.2f} tCO2 (用户: {user_co2_t:,.2f} tCO2)")
print(f"  差异: {abs(ce['total_emission_tons']-user_co2_t)/user_co2_t*100:.2f}%")
print(f"  碳强度: {carbon_per_m2:.2f} kgCO2/m2 (用户: {USER_REF['carbon_per_m2']:.2f})")

# [3] Standard Comparison
sc = compare_with_standard(coal_per_m2, carbon_per_m2, '酒店', '苏州',
                           star_rating='五星级', climate_zone='夏热冬冷I区')
print(f"\n[3] 标准对标 (三级判定)")
print(f"  标准: {sc['standard_source']}")
print(f"  类型: {sc.get('building_type', 'N/A')} | 气候区: {sc.get('climate_zone', 'N/A')}")
print(f"\n  能耗: {sc['energy_icon']} {sc['energy_level']}")
print(f"    实际: {sc['energy_actual']} {sc['energy_unit']}")
print(f"    引导: {sc['energy_guide']} | 基准: {sc['energy_benchmark']} | 约束: {sc['energy_constraint']}")
print(f"    判定: {sc['energy_message']}")
print(f"\n  碳排放: {sc['carbon_icon']} {sc['carbon_level']}")
print(f"    实际: {sc['carbon_actual']} {sc['carbon_unit']}")
print(f"    引导: {sc['carbon_guide']} | 基准: {sc['carbon_benchmark']} | 约束: {sc['carbon_constraint']}")
print(f"    判定: {sc['carbon_message']}")
print(f"\n  节能建议: {sc['suggestion']}")

print(f"\n{SEP}")
print("  验证完成!")
print(SEP)
