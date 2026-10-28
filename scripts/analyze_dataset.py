#!/usr/bin/env python3
"""Generate descriptive EDA tables, charts, and a concise Markdown report."""
import csv
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'dataset.csv'
OUT = ROOT / 'data' / 'analysis'
FIG = OUT / 'figures'


def read_rows(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write_table(path, headers, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def save_bar(path, title, labels, values, ylabel, rotate=0):
    fig, ax = plt.subplots(figsize=(10, 5.4))
    bars = ax.bar(labels, values, color='#3568a8')
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis='y', alpha=.22)
    ax.bar_label(bars, padding=3, fmt='%.2f' if any(isinstance(v, float) for v in values) else '%d')
    if rotate:
        plt.setp(ax.get_xticklabels(), rotation=rotate, ha='right')
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    rows = read_rows(SOURCE)
    intents = sorted({r['intent'] for r in rows})
    intent_counts = Counter(r['intent'] for r in rows)
    escalated_counts = Counter(r['intent'] for r in rows if r['escalated'] == '1')
    rates = {i: escalated_counts[i] / intent_counts[i] for i in intents}
    ratings = Counter(int(r['user_rating']) for r in rows)
    conf = {flag: [float(r['confidence_score']) for r in rows if r['escalated'] == flag] for flag in ('0','1')}
    query_lens = [len(r['paraphrased_query']) for r in rows]
    dates = [datetime.strptime(r['timestamp'], '%Y-%m-%d %H:%M:%S') for r in rows]
    days = Counter(d.strftime('%Y-%m-%d') for d in dates)
    weekdays = Counter(d.strftime('%A') for d in dates)
    hours = Counter(d.hour for d in dates)
    anomalies = [r for r in rows if r['is_anomaly'] == '1']
    normal = [r for r in rows if r['is_anomaly'] != '1']

    # PIIs should already be masked; count only likely unmasked patterns. These are
    # a heuristic audit, not a guarantee of anonymization.
    email_re = re.compile(r'(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b')
    phone_re = re.compile(r'(?<!\w)(?:\+?\d[\d ()-]{8,}\d)(?!\w)')
    email_hits = sum(bool(email_re.search(r['paraphrased_query'])) for r in rows)
    phone_hits = sum(bool(phone_re.search(r['paraphrased_query'])) for r in rows)
    duplicate_groups = defaultdict(list)
    for r in rows:
        duplicate_groups[' '.join(r['paraphrased_query'].casefold().split())].append(r)
    repeated_groups = [g for g in duplicate_groups.values() if len(g) > 1]
    mixed_label_groups = [g for g in repeated_groups if len({r['intent'] for r in g}) > 1]

    write_table(OUT/'intent_distribution.csv', ['intent','count','percent'], [[i,intent_counts[i],round(100*intent_counts[i]/len(rows),2)] for i in intents])
    write_table(OUT/'escalation_by_intent.csv', ['intent','rows','escalated','escalation_rate_percent'], [[i,intent_counts[i],escalated_counts[i],round(100*rates[i],2)] for i in intents])
    write_table(OUT/'rating_distribution.csv', ['rating','count'], [[r,ratings[r]] for r in range(1,6)])
    write_table(OUT/'confidence_by_escalation.csv', ['escalated','count','mean_confidence','median_confidence'], [[flag,len(vals),round(statistics.mean(vals),4),round(statistics.median(vals),4)] for flag,vals in [('0',conf['0']),('1',conf['1'])]])
    write_table(OUT/'weekday_counts.csv', ['weekday','count'], [[d,weekdays[d]] for d in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']])
    write_table(OUT/'hour_counts.csv', ['hour_24h','count'], [[h,hours[h]] for h in range(24)])
    write_table(OUT/'daily_counts.csv', ['date','count'], sorted(days.items()))
    write_table(OUT/'anomaly_by_type.csv', ['user_query_type','count'], [[k,v] for k,v in sorted(Counter(r['user_query_type'] for r in anomalies).items())])

    save_bar(FIG/'intent_distribution.png','Intent distribution',intents,[intent_counts[i] for i in intents],'Rows',45)
    save_bar(FIG/'escalation_by_intent.png','Escalation rate by intent',intents,[100*rates[i] for i in intents],'Escalated (%)',45)
    save_bar(FIG/'rating_distribution.png','User rating distribution',[str(i) for i in range(1,6)],[ratings[i] for i in range(1,6)],'Rows')
    fig, ax = plt.subplots(figsize=(9,5.2))
    bins=[i/20 for i in range(21)]
    ax.hist(conf['0'],bins=bins,alpha=.65,label='Not escalated',color='#4c9f70')
    ax.hist(conf['1'],bins=bins,alpha=.65,label='Escalated',color='#d47a42')
    ax.set(title='Logged confidence by escalation status',xlabel='Original system confidence',ylabel='Rows')
    ax.legend(); ax.grid(axis='y',alpha=.2); fig.tight_layout(); fig.savefig(FIG/'confidence_by_escalation.png',dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10,5.2))
    ax.hist(query_lens,bins=20,color='#7664a8',edgecolor='white')
    ax.set(title='Query length distribution',xlabel='Characters per query',ylabel='Rows')
    ax.grid(axis='y',alpha=.2); fig.tight_layout(); fig.savefig(FIG/'query_length_distribution.png',dpi=160); plt.close(fig)
    daily=sorted(days.items())
    fig, ax = plt.subplots(figsize=(11,5.2))
    ax.plot([d for d,_ in daily],[n for _,n in daily],color='#3568a8',linewidth=1.4)
    ax.set(title='Queries per day',xlabel='Date',ylabel='Rows'); ax.tick_params(axis='x',rotation=45); ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(FIG/'queries_per_day.png',dpi=160); plt.close(fig)
    save_bar(FIG/'queries_by_weekday.png','Queries by weekday',['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],[weekdays[d] for d in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']],'Rows')

    ranked=sorted(rates.items(),key=lambda x:x[1],reverse=True)
    biggest=max(intent_counts,key=intent_counts.get)
    smallest=min(intent_counts,key=intent_counts.get)
    avg_conf0=statistics.mean(conf['0']); avg_conf1=statistics.mean(conf['1'])
    report=f'''# Dataset EDA and preprocessing notes

Generated from the 5,000-row `dataset.csv`; raw data was not modified. Charts and CSV tables are in this folder.

## Main observations

- The most frequent intent is **{biggest}** ({intent_counts[biggest]:,} rows); the least frequent is **{smallest}** ({intent_counts[smallest]:,}). See `intent_distribution.csv` and `figures/intent_distribution.png`.
- Escalation rate is highest for **{ranked[0][0]}** ({ranked[0][1]:.1%}) and lowest for **{ranked[-1][0]}** ({ranked[-1][1]:.1%}). These are observed historical labels, not policy targets.
- Ratings: {', '.join(f'{i}: {ratings[i]:,}' for i in range(1,6))}. See `rating_distribution.csv`.
- Original logged confidence averages {avg_conf0:.3f} for non-escalated rows and {avg_conf1:.3f} for escalated rows. Treat this column as descriptive only; do not use it as a model feature because it was produced by the prior system.
- Query length: median {statistics.median(query_lens):.0f} characters; range {min(query_lens)}–{max(query_lens)} characters.
- Timestamps span {min(dates):%Y-%m-%d} through {max(dates):%Y-%m-%d}. See daily, weekday, and hour count tables and charts.
- {len(anomalies)} rows are flagged as anomalies across {len(set(r['user_query_type'] for r in anomalies))} anomaly/fault types. Their intent labels are ordinary helpdesk intents, and there is no `out_of_scope` label. Keep these out of normal intent training until reviewed; construct a separately reviewed OOD evaluation set.
- There are {len(repeated_groups)} repeated normalized-query groups, with {len(mixed_label_groups)} groups that have conflicting intent labels. The split script keeps every repeated query in one partition, but conflicting labels still need manual review.
- Heuristic PII scan found {email_hits} email-like and {phone_hits} phone-like query strings. This pattern scan is not proof that all PII is absent; the data contains redaction markers, and a dedicated scrubber should be applied before any persistent logs.

## Preprocessing decisions for modeling

1. Preserve the raw source file. Apply transformations in the model pipeline or to generated copies only.
2. Normalize text with Unicode normalization, case-folding, and whitespace trimming. Mask URLs, email addresses, phone numbers, and student/roll numbers before storage and model input.
3. Do not remove stopwords aggressively; short queries may depend on them. Do not include `confidence_score`, `escalated`, `user_rating`, `resolution_status`, `timestamp`, `session_id`, or `is_anomaly` as intent-model features.
4. Use the grouped split files under `data/splits/`. Tune preprocessing and thresholds on train/validation only; use test once for final metrics.
5. Review the five mixed-label duplicate groups and all anomaly examples. Add a dedicated `out_of_scope` class only after deciding and validating labels; do not infer it from anomalous wording alone.
6. The FAQ file is mock content and must not be used for student-facing answers until its answers are replaced with sourced university information.

## Figures

- Intent counts: `figures/intent_distribution.png`
- Escalation by intent: `figures/escalation_by_intent.png`
- Ratings: `figures/rating_distribution.png`
- Confidence by escalation: `figures/confidence_by_escalation.png`
- Query lengths: `figures/query_length_distribution.png`
- Queries per day: `figures/queries_per_day.png`
- Queries by weekday: `figures/queries_by_weekday.png`
'''
    (OUT/'REPORT.md').write_text(report,encoding='utf-8')
    print(f'Analyzed {len(rows)} rows; wrote EDA tables and 7 charts to {OUT}')

if __name__ == '__main__':
    main()
