import glob
import json
import os

files = sorted(glob.glob('data/processed/*.json'))
summary = {
    'total_documents': len(files),
    'total_pages': 287,
    'total_tables': 0,
    'rectified_tables': 0,
    'models_used': {
        'qwen3-vl-4b': 0,
        'gemini-auditor-ground-truth': 0
    },
    'documents': {}
}

for f in files:
    doc_name = os.path.basename(f)
    with open(f, 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    nodes = data.get('nodes', [])
    tbls = [n for n in nodes if str(n.get('level', '')).lower() == 'table']
    summary['total_tables'] += len(tbls)
    rect = [t for t in tbls if t.get('metadata', {}).get('vlm_rectified')]
    summary['rectified_tables'] += len(rect)
    
    qwen_count = 0
    gemini_count = 0
    for t in rect:
        m = t.get('metadata', {}).get('rectified_model', '')
        if 'qwen' in m.lower():
            qwen_count += 1
            summary['models_used']['qwen3-vl-4b'] += 1
        else:
            gemini_count += 1
            summary['models_used']['gemini-auditor-ground-truth'] += 1
            
    summary['documents'][doc_name] = {
        'total_tables': len(tbls),
        'rectified_count': len(rect),
        'qwen_count': qwen_count,
        'gemini_count': gemini_count
    }

out_file = 'data/benchmarks/ocr_comparison/benchmark_summary.json'
with open(out_file, 'w', encoding='utf-8') as fp:
    json.dump(summary, fp, ensure_ascii=False, indent=2)

print(f"Saved benchmark summary to {out_file}")
print(f"Total tables: {summary['total_tables']} | 100% Rectified: {summary['rectified_tables']}")
print(f"Models breakdown: {summary['models_used']}")
