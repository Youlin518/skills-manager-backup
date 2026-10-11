"""生成苏州高铁金科大酒店能耗分析 Word 报告"""
import sys, json, os
sys.path.insert(0, '.claude/skills/building-energy-analysis/scripts')
from energy_analysis import calc_energy_proportion, calc_monthly_trend, calc_unit_area_intensity
from carbon_calculation import calc_carbon_emission, compare_with_standard
from generate_report import generate_report

BUILDING = {
    'name': '苏州高铁金科大酒店',
    'area': 56846,
    'type': '酒店',
    'location': '苏州',
    'year': 2025,
}

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

AREA = BUILDING['area']
PROVINCE = '苏州'
BUILDING_TYPE = '酒店'
STAR = '五星级'
ZONE = '夏热冬冷I区'

print("Generating analysis...")

# Energy
ep = calc_energy_proportion(energy_data)
mt = calc_monthly_trend(energy_data)
ui = calc_unit_area_intensity(energy_data, AREA)
total_coal = ep['total_coal_kgce']
coal_per_m2 = total_coal / AREA

# Carbon
ce = calc_carbon_emission(energy_data, PROVINCE)
carbon_per_m2 = ce['total_emission_tons'] * 1000 / AREA

# Standard
sc = compare_with_standard(coal_per_m2, carbon_per_m2, BUILDING_TYPE, PROVINCE,
                           star_rating=STAR, climate_zone=ZONE)

# Assemble
data = {
    'building_info': BUILDING,
    'energy_proportion': ep,
    'monthly_trend': mt,
    'unit_area_intensity': ui,
    'carbon_emission': ce,
    'carbon_intensity_kgco2_per_m2': round(carbon_per_m2, 2),
    'total_coal_kgce': round(total_coal, 2),
    'coal_per_m2_kgce': round(coal_per_m2, 2),
    'standard_comparison': sc,
}

# Print summary
print(f"  Total Coal: {total_coal:,.1f} kgce")
print(f"  Coal/m2: {coal_per_m2:.2f} kgce/m2")
print(f"  Total CO2: {ce['total_emission_tons']:,.2f} t")
print(f"  CO2/m2: {carbon_per_m2:.2f} kgCO2/m2")
print(f"  Energy: {sc['energy_icon']} {sc['energy_level']}")
print(f"  Carbon: {sc['carbon_icon']} {sc['carbon_level']}")
print(f"  Grid factor: {ce['grid_factor_used']}")

# Generate Word report
output_path = r'C:\Users\86158\Desktop\苏州高铁金科大酒店节能改造\能耗分析报告_2025.docx'
print(f"\nGenerating Word report...")
result = generate_report(data, output_path)
print(f"Report saved: {result}")
print("Done!")
