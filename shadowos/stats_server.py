#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

class DownloadStats:
    def __init__(self, stats_file='download_stats.json'):
        self.stats_file = stats_file
        self.data = self.load()

    def load(self):
        if Path(self.stats_file).exists():
            with open(self.stats_file) as f:
                return json.load(f)
        return {
            'total_downloads': 0,
            'by_version': {},
            'by_region': {},
            'by_os': {},
            'unique_ips': set(),
            'last_updated': datetime.now().isoformat()
        }

    def record_download(self, version, region='unknown', source_os='unknown', ip='unknown'):
        self.data['total_downloads'] += 1

        # By version
        if version not in self.data['by_version']:
            self.data['by_version'][version] = 0
        self.data['by_version'][version] += 1

        # By region
        if region not in self.data['by_region']:
            self.data['by_region'][region] = 0
        self.data['by_region'][region] += 1

        # By source OS
        if source_os not in self.data['by_os']:
            self.data['by_os'][source_os] = 0
        self.data['by_os'][source_os] += 1

        self.data['last_updated'] = datetime.now().isoformat()
        self.save()

    def save(self):
        with open(self.stats_file, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)

    def get_report(self):
        return {
            'summary': {
                'total': self.data['total_downloads'],
                'versions': len(self.data['by_version']),
                'regions': len(self.data['by_region']),
                'updated': self.data['last_updated']
            },
            'by_version': self.data['by_version'],
            'by_region': self.data['by_region'],
            'by_source_os': self.data['by_os']
        }

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        stats = DownloadStats()
        print(json.dumps(stats.get_report(), indent=2))
    else:
        cmd = sys.argv[1]
        if cmd == 'record':
            stats = DownloadStats()
            version = sys.argv[2] if len(sys.argv) > 2 else 'unknown'
            region = sys.argv[3] if len(sys.argv) > 3 else 'unknown'
            stats.record_download(version, region)
            print(f"Recorded: {version} from {region}")
