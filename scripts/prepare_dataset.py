#!/usr/bin/env python3
"""Create reproducible query-grouped train/validation/test CSVs."""
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'dataset.csv'
OUT = ROOT / 'data' / 'splits'
SEED = 42
SPLITS = (('train', 0.70), ('validation', 0.10), ('test', 0.20))


def norm_query(text):
    return ' '.join(text.casefold().split())


def read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    rows = read_csv(INPUT)
    fields = list(rows[0])
    grouped = defaultdict(list)
    for row in rows:
        grouped[norm_query(row['paraphrased_query'])].append(row)

    # A query group should have one anomaly status. Fail closed if that changes.
    for query, members in grouped.items():
        if len({r['is_anomaly'] for r in members}) != 1:
            raise ValueError(f'Anomaly label conflicts within duplicate query group: {query!r}')

    regular = [rs for rs in grouped.values() if rs[0]['is_anomaly'] != '1']
    anomalies = [r for rs in grouped.values() if rs[0]['is_anomaly'] == '1' for r in rs]

    # Stratify by the most common intent in each query group, assigning all duplicate
    # rows as one unit. Any mixed-label group stays intact and is documented.
    by_intent = defaultdict(list)
    conflict_groups = []
    for members in regular:
        labels = Counter(r['intent'] for r in members)
        if len(labels) > 1:
            conflict_groups.append(members)
        dominant = sorted(labels.items(), key=lambda x: (-x[1], x[0]))[0][0]
        by_intent[dominant].append(members)

    rng = random.Random(SEED)
    assigned = {name: [] for name, _ in SPLITS}
    for intent in sorted(by_intent):
        groups = by_intent[intent]
        rng.shuffle(groups)
        groups.sort(key=len, reverse=True)
        targets = {name: sum(len(g) for g in groups) * ratio for name, ratio in SPLITS}
        counts = {name: 0 for name, _ in SPLITS}
        for group in groups:
            # Pick the split furthest below its target proportion for this intent.
            name = max((n for n, _ in SPLITS), key=lambda n: (targets[n] - counts[n], -counts[n]))
            assigned[name].extend(group)
            counts[name] += len(group)

    # Stable row order within each split, matching the source file.
    position = {r['session_id']: i for i, r in enumerate(rows)}
    for name in assigned:
        assigned[name].sort(key=lambda r: position[r['session_id']])
    OUT.mkdir(parents=True, exist_ok=True)
    for name in assigned:
        write_csv(OUT / f'{name}.csv', assigned[name], fields)
    write_csv(OUT / 'anomaly_holdout.csv', sorted(anomalies, key=lambda r: position[r['session_id']]), fields)

    # Validate that every query string occurs in exactly one output partition.
    query_partition = {}
    for part, part_rows in assigned.items():
        for row in part_rows:
            q = norm_query(row['paraphrased_query'])
            if q in query_partition and query_partition[q] != part:
                raise AssertionError(f'Duplicate query leaked across splits: {q!r}')
            query_partition[q] = part
    if set(query_partition) & {norm_query(r['paraphrased_query']) for r in anomalies}:
        raise AssertionError('Anomaly query overlaps a standard split')

    summary = [
        '# Dataset preparation summary', '',
        f'- Source: `dataset.csv` ({len(rows):,} rows).',
        f'- Grouping: case-folded, whitespace-normalized `paraphrased_query`; all identical query text stays in one partition.',
        f'- Seed: {SEED}; approximate target proportions among non-anomaly rows: 70% / 10% / 20%.',
        '- Anomaly rows are excluded from standard intent-classifier splits because they are labeled with ordinary intents and there is no `out_of_scope` intent. They are preserved in `anomaly_holdout.csv` for separate OOD/safety evaluation.',
        f'- Repeated query groups in the full source: {sum(len(g)>1 for g in grouped.values()):,}; groups with conflicting intent labels: {len([g for g in grouped.values() if len({r["intent"] for r in g})>1]):,}.',
        '- Mixed-label duplicate query groups remain intact in one split; inspect these labels before training.', '',
        '| Partition | Rows | Intent counts |', '|---|---:|---|'
    ]
    for name, _ in SPLITS:
        part_rows = assigned[name]
        intents = Counter(r['intent'] for r in part_rows)
        summary.append(f"| `{name}.csv` | {len(part_rows):,} | " + ', '.join(f'{k}: {v}' for k,v in sorted(intents.items())) + ' |')
    summary.append(f'| `anomaly_holdout.csv` | {len(anomalies):,} | ' + ', '.join(f'{k}: {v}' for k,v in sorted(Counter(r['intent'] for r in anomalies).items())) + ' |')
    summary.extend(['', 'Before training, decide how to represent out-of-scope examples and review the conflicting-label groups. The anomaly holdout is not a substitute for a clean, human-reviewed OOD test set.', ''])
    (OUT / 'README.md').write_text('\n'.join(summary), encoding='utf-8')
    print(f"Created splits: {', '.join(f'{k}={len(v)}' for k,v in assigned.items())}; anomaly_holdout={len(anomalies)}")

if __name__ == '__main__':
    main()
