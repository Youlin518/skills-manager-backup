"""运行所有 eval 测试用例，展示完整分析结果"""
import subprocess
import json
import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'
ENCODING = 'utf-8'
SCRIPT_DIR = '.claude/skills/building-energy-analysis'

def run(cmd, stdin_data=None):
    """Run a command and return (stdout, stderr, returncode)."""
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    r = subprocess.run(cmd, input=stdin_data, capture_output=True,
                       encoding=ENCODING, errors='replace', env=env)
    return r.stdout, r.stderr, r.returncode


def test_case(name, data_file, province, building_type):
    """Run a full test case through the pipeline."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

    # Parse
    stdout, stderr, rc = run([
        'python', '-X', 'utf8',
        f'{SCRIPT_DIR}/scripts/parse_data.py', data_file
    ])
    if rc != 0 or not stdout.strip():
        print(f"  PARSE ERROR: {stderr}")
        return None
    parsed = json.loads(stdout)
    bi = parsed.get('building_info', {})
    ed = parsed.get('energy_data', [])

    print(f"\n  📋 基本信息:")
    print(f"     建筑: {bi.get('name', 'N/A')}")
    print(f"     面积: {bi.get('area', 0):.0f} m²")
    print(f"     类型: {bi.get('type', 'N/A')}")
    print(f"     地点: {bi.get('location', 'N/A')}")
    print(f"     数据: {len(ed)} 个月")

    # Energy Analysis
    stdout2, stderr2, rc2 = run([
        'python', '-X', 'utf8',
        f'{SCRIPT_DIR}/scripts/energy_analysis.py'
    ], stdin_data=stdout)
    if rc2 != 0 or not stdout2.strip():
        print(f"  ENERGY ERROR: {stderr2}")
        return None
    en = json.loads(stdout2)

    ep = en.get('energy_proportion', {})
    print(f"\n  ⚡ 能源比例分析:")
    print(f"     总标煤量: {ep.get('total_coal_kgce', 0):,.1f} kgce ({ep.get('total_coal_kgce', 0)/1000:,.1f} tce)")
    for p in ep.get('proportions', []):
        print(f"     {p['label']:6s}: {p['coal_equiv_kgce']:>12,.1f} kgce  ({p['proportion_pct']:>5.1f}%)")

    mt = en.get('monthly_trend', {})
    pk = mt.get('peak_month', {})
    vl = mt.get('valley_month', {})
    print(f"\n  📈 逐月趋势:")
    print(f"     峰值月: {pk.get('month')} 月 ({pk.get('total_coal_kgce', 0):,.0f} kgce)")
    print(f"     谷值月: {vl.get('month')} 月 ({vl.get('total_coal_kgce', 0):,.0f} kgce)")
    if pk.get('total_coal_kgce', 0) > 0 and vl.get('total_coal_kgce', 0) > 0:
        ratio = pk['total_coal_kgce'] / vl['total_coal_kgce']
        print(f"     峰谷比: {ratio:.2f}")

    seasonal = mt.get('seasonal_analysis', {}).get('season_data', {})
    if seasonal:
        dominant = mt.get('seasonal_analysis', {}).get('dominant_season', '')
        print(f"     主导季节: {dominant}")
        for sname, sdata in seasonal.items():
            print(f"     {sname}: {sdata['avg_coal_kgce']:,.0f} kgce ({sdata.get('pct_of_annual', 0)}%)")

    anomalies = mt.get('anomalies', [])
    if anomalies:
        print(f"     ⚠ 异常月: {len(anomalies)} 个")
        for a in anomalies:
            print(f"       {a['month']}月: {a['type']} (均值的 {a['ratio']}x)")

    ui = en.get('unit_area_intensity', {})
    if not ui.get('error'):
        print(f"\n  📐 单位面积指标:")
        print(f"     综合能耗: {ui.get('total_coal_per_m2', 0):.2f} kgce/m²·a")
        print(f"     电力: {ui.get('electricity_per_m2', 0):.2f} kWh/m²")
        if ui.get('gas_per_m2', 0) > 0.001:
            print(f"     天然气: {ui.get('gas_per_m2', 0):.4f} m³/m²")
        if ui.get('heat_per_m2', 0) > 0.001:
            print(f"     热力: {ui.get('heat_per_m2', 0):.4f} GJ/m²")

    # Carbon Calculation
    stdout3, stderr3, rc3 = run([
        'python', '-X', 'utf8',
        f'{SCRIPT_DIR}/scripts/carbon_calculation.py'
    ], stdin_data=stdout)
    # Pass province and building_type via separate mechanism
    # Actually, let me add them to the JSON data
    if province or building_type:
        parsed_copy = json.loads(stdout)
        parsed_copy['_province'] = province
        parsed_copy['_building_type'] = building_type
        stdout3, stderr3, rc3 = run([
            'python', '-X', 'utf8',
            f'{SCRIPT_DIR}/scripts/carbon_calculation.py',
            json.dumps(parsed_copy, ensure_ascii=False),
            province, building_type
        ])
    else:
        stdout3, stderr3, rc3 = run([
            'python', '-X', 'utf8',
            f'{SCRIPT_DIR}/scripts/carbon_calculation.py'
        ], stdin_data=stdout)

    if rc3 != 0 or not stdout3.strip():
        print(f"  CARBON ERROR: {stderr3}")
        return None
    ce = json.loads(stdout3)

    print(f"\n  🌍 碳排放计算:")
    print(f"     区域: {ce.get('region', 'N/A')}")
    print(f"     电网因子: {ce.get('grid_factor_used', 0)} kgCO₂/kWh")
    print(f"     总排放: {ce.get('total_emission_tons', 0):,.2f} tCO₂")

    for key, val in ce.get('emission_breakdown', {}).items():
        co2 = val.get('co2_tons', 0)
        pct = val.get('pct', 0)
        if co2 > 0.01:
            print(f"     {key:12s}: {co2:>10,.2f} tCO₂ ({pct:>5.1f}%)")

    if not ce.get('carbon_intensity_kgco2_per_m2') and not ce.get('error'):
        area = bi.get('area', 0)
        if area > 0:
            ci = ce.get('total_emission_tons', 0) * 1000 / area
            print(f"     碳强度: {ci:.2f} kgCO₂/m²·a")

    if ce.get('carbon_intensity_kgco2_per_m2'):
        print(f"     碳强度: {ce['carbon_intensity_kgco2_per_m2']:.2f} kgCO₂/m²·a")

    sc = ce.get('standard_comparison', {})
    print(f"\n  🎯 标准对标:")
    if sc.get('status') == 'matched':
        print(f"     判定: {sc.get('icon', '')} {sc.get('level', 'N/A')}")
        print(f"     标准: {sc.get('standard_source', 'N/A')}")
        print(f"     实际: {sc.get('actual_value', 0):.2f}")
        print(f"     约束: {sc.get('constraint_value', 0)} {sc.get('unit', '')}")
        print(f"     引导: {sc.get('guide_value', 0)} {sc.get('unit', '')}")
        print(f"     建议: {sc.get('suggestion', '')}")
    else:
        print(f"     {sc.get('message', 'N/A')}")

    return {'parsed': parsed, 'energy': en, 'carbon': ce}


# Run all test cases
print("=" * 60)
print("  建筑能耗分析 Skill — 测试报告")
print("=" * 60)

# Case 1: Beijing Office
test_case(
    "Case 1: 北京中关村科技大厦 (办公建筑)",
    f"{SCRIPT_DIR}/evals/eval1_beijing_office.txt",
    "北京", "办公"
)

# Case 2: Shanghai Commercial (from test_input.txt)
test_case(
    "Case 2: 上海恒隆广场 (商业建筑)",
    f"{SCRIPT_DIR}/evals/test_input.txt",
    "上海", "商业"
)

print(f"\n{'='*60}")
print("  所有测试用例执行完毕")
print(f"{'='*60}")
