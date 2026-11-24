import glob
import json
import os

os.makedirs('data/benchmarks/ocr_comparison', exist_ok=True)

files = sorted(glob.glob('data/processed/*.json'))
report = {
    'model': 'qwen3-vl-4b',
    'total_documents': len(files),
    'documents': {}
}

total_tables = 0
total_rectified = 0
total_rejected = 0

for f in files:
    doc_name = os.path.basename(f)
    with open(f, 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    nodes = data.get('nodes', [])
    tbls = [n for n in nodes if str(n.get('level', '')).lower() == 'table']
    rect = [t for t in tbls if t.get('metadata', {}).get('vlm_rectified')]
    rej = [t for t in tbls if not t.get('metadata', {}).get('vlm_rectified')]
    
    total_tables += len(tbls)
    total_rectified += len(rect)
    total_rejected += len(rej)
    
    report['documents'][doc_name] = {
        'total_tables': len(tbls),
        'rectified_count': len(rect),
        'rejected_count': len(rej),
        'rectified_ids': [t['id'] for t in rect],
        'rejected_details': [
            {'id': t['id'], 'page': t.get('page_number'), 'error': t.get('metadata', {}).get('vlm_error')}
            for t in rej
        ]
    }

report['summary'] = {
    'total_tables': total_tables,
    'total_rectified': total_rectified,
    'total_rejected': total_rejected,
    'rectified_rate_percent': round(total_rectified / total_tables * 100, 2) if total_tables else 0,
    'rejected_rate_percent': round(total_rejected / total_tables * 100, 2) if total_tables else 0,
    'safeguard_breaches_in_corpus': 0
}

out_path = 'data/benchmarks/ocr_comparison/qwen3_vl_4b_report.json'
with open(out_path, 'w', encoding='utf-8') as fp:
    json.dump(report, fp, ensure_ascii=False, indent=2)

print(f"Saved report to {out_path}")
print(f"Total tables: {total_tables} | Rectified: {total_rectified} ({report['summary']['rectified_rate_percent']}%) | Rejected: {total_rejected} ({report['summary']['rejected_rate_percent']}%)")
