"""生成上海中医药大学 DB31/T 783-2026 标准能耗分析报告"""
import sys, json, os
sys.path.insert(0, '.claude/skills/building-energy-analysis/scripts')
from energy_analysis import calc_energy_proportion, calc_monthly_trend, calc_unit_area_intensity
from carbon_calculation import calc_carbon_emission, compare_with_standard
from generate_report import generate_report

AREA = 155500
BUILDING_NAME = '上海中医药大学张江校区'
PROVINCE = '上海'
BUILDING_TYPE = '学校'

dec_est = round((2382361 + 3402180) / 2)
energy_data = [
    {'month': 1, 'electricity_kwh': 3402180.0, 'gas_m3': 17771.0, 'heat_gj': 0},
    {'month': 2, 'electricity_kwh': 2411725.0, 'gas_m3': 13214.0, 'heat_gj': 0},
    {'month': 3, 'electricity_kwh': 2913094.0, 'gas_m3': 6496.0, 'heat_gj': 0},
    {'month': 4, 'electricity_kwh': 2159325.0, 'gas_m3': 18969.0, 'heat_gj': 0},
    {'month': 5, 'electricity_kwh': 2417756.0, 'gas_m3': 17444.0, 'heat_gj': 0},
    {'month': 6, 'electricity_kwh': 2948339.0, 'gas_m3': 15783.0, 'heat_gj': 0},
    {'month': 7, 'electricity_kwh': 4043817.0, 'gas_m3': 14300.0, 'heat_gj': 0},
    {'month': 8, 'electricity_kwh': 4027505.0, 'gas_m3': 8128.0, 'heat_gj': 0},
    {'month': 9, 'electricity_kwh': 3924629.0, 'gas_m3': 7106.0, 'heat_gj': 0},
    {'month': 10, 'electricity_kwh': 2447077.0, 'gas_m3': 16171.0, 'heat_gj': 0},
    {'month': 11, 'electricity_kwh': 2382361.0, 'gas_m3': 17775.0, 'heat_gj': 0},
    {'month': 12, 'electricity_kwh': dec_est, 'gas_m3': 18474.0, 'heat_gj': 0},
]

# Analysis
ep = calc_energy_proportion(energy_data)
total_coal = ep['total_coal_kgce']
mt = calc_monthly_trend(energy_data)
ui = calc_unit_area_intensity(energy_data, AREA)
ce = calc_carbon_emission(energy_data, PROVINCE)
coal_per_m2 = total_coal / AREA
carbon_per_m2 = ce['total_emission_tons'] * 1000 / AREA

# Standard: DB31/T 783-2026, α1默认1.0, α2=2.0(医学)
sc = compare_with_standard(coal_per_m2, carbon_per_m2, BUILDING_TYPE, PROVINCE,
                           alpha1=1.0, alpha2=2.0)

print(f'总标煤: {total_coal:,.0f} kgce ({total_coal/1000:,.1f} tce)')
print(f'单位面积(未修正): {coal_per_m2:.2f} kgce/m2.a')
print(f'单位面积(修正后): {sc["coal_per_m2_corrected"]:.2f} kgce/m2.a')
print(f'对标: {sc["energy_icon"]} {sc["energy_level"]}')
print(f'公式: {sc["correction_formula"]}')
print(f'碳排放: {ce["total_emission_tons"]:,.2f} tCO2')

combined = {
    'building_info': {'name': BUILDING_NAME, 'area': AREA, 'type': BUILDING_TYPE,
                       'location': PROVINCE, 'year': 2024},
    'energy_proportion': ep,
    'monthly_trend': mt,
    'unit_area_intensity': ui,
    'carbon_emission': ce,
    'carbon_intensity_kgco2_per_m2': round(carbon_per_m2, 2),
    'total_coal_kgce': round(total_coal, 2),
    'coal_per_m2_kgce': round(sc.get('coal_per_m2_corrected', coal_per_m2), 2),
    'standard_comparison': sc,
    'data_notes': [
        '燃气数据仅含学生食堂，不含校区其他燃气使用。',
        '12月用电量为估算值（取11月与1月均值），原始数据仅含1-11月。',
        f'修正系数：α1=1.0（默认，设备资产未知），α2=2.0（医学）。如需精确值请提供教学科研设备资产总额。',
        'DB31/T 783-2026 附录A未规定碳排放因子，碳排放采用华东区域电网排放因子0.5698 kgCO₂/kWh计算。',
    ],
}

output = r'C:\Users\86158\Desktop\苏州高铁金科大酒店节能改造\中医药\上中医张江校区_能耗分析报告_2024_DB31T783.docx'
generate_report(combined, output)
print(f'Report saved: {output}')
