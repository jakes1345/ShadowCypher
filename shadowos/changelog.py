#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime
from pathlib import Path

def get_commits_since_tag(tag):
    """Get all commits since the last tag"""
    try:
        output = subprocess.check_output(
            ['git', 'log', f'{tag}..HEAD', '--pretty=format:%H|%s|%b|%an|%ae|%ai'],
            text=True
        )
        return output.strip().split('\n') if output.strip() else []
    except subprocess.CalledProcessError:
        return []

def parse_commit(line):
    """Parse commit into structured data"""
    parts = line.split('|')
    if len(parts) < 5:
        return None
    hash, subject, body, author, email, date = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5] if len(parts) > 5 else ''

    category = 'other'
    if subject.startswith('feat'):
        category = 'features'
    elif subject.startswith('fix'):
        category = 'bugfixes'
    elif subject.startswith('perf'):
        category = 'performance'
    elif subject.startswith('security'):
        category = 'security'

    return {
        'hash': hash[:7],
        'subject': subject,
        'category': category,
        'author': author,
        'email': email
    }

def generate_changelog(version, commits):
    """Generate changelog markdown entry"""
    lines = [f"## [{version}] - {datetime.now().strftime('%Y-%m-%d')}\n"]

    categories = {}
    for commit in commits:
        if not commit:
            continue
        cat = commit['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(commit)

    order = ['security', 'features', 'bugfixes', 'performance', 'other']
    for cat in order:
        if cat in categories:
            lines.append(f"\n### {cat.title()}\n")
            for commit in categories[cat]:
                lines.append(f"- {commit['subject']} ({commit['hash']})")

    return '\n'.join(lines)

if __name__ == '__main__':
    import sys
    version = sys.argv[1] if len(sys.argv) > 1 else 'Unreleased'

    # Get last tag
    try:
        last_tag = subprocess.check_output(['git', 'describe', '--tags', '--abbrev=0'], text=True).strip()
    except:
        last_tag = ''

    commits_data = get_commits_since_tag(last_tag)
    commits = [parse_commit(c) for c in commits_data]

    changelog = generate_changelog(version, commits)
    print(changelog)
