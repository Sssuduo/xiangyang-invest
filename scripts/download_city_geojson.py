"""
下载全国所有地级市 GeoJSON 数据并合并为单一文件。
数据源：阿里云 DataV.GeoAtlas API
输出：static/data/china_cities.json
"""
import json
import time
import urllib.request
import os
import sys

# 中国 31 个大陆省级行政区 adcode（台湾/香港/澳门由 DataV 维护但格式不同，跳过）
PROVINCE_ADCODES = [
    110000, 120000, 130000, 140000, 150000,
    210000, 220000, 230000,
    310000, 320000, 330000, 340000, 350000, 360000, 370000,
    410000, 420000, 430000, 440000, 450000, 460000,
    500000, 510000, 520000, 530000, 540000,
    610000, 620000, 630000, 640000, 650000,
]

BASE_URL = 'https://geo.datav.aliyun.com/areas_v3/bound/{}_full.json'
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'data', 'china_cities.json')


def fetch_json(url, retries=3):
    """带重试的 HTTP GET"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f'  ERROR: {e}')
                return None


def main():
    all_features = []
    total = len(PROVINCE_ADCODES)
    skipped = 0

    print(f'Downloading city GeoJSON for {total} provinces...')
    print('-' * 50)

    for idx, adcode in enumerate(PROVINCE_ADCODES):
        url = BASE_URL.format(adcode)
        print(f'[{idx+1:2d}/{total}] Downloading {adcode}...', end=' ', flush=True)

        data = fetch_json(url)
        if not data or 'features' not in data:
            print('(skip)')
            skipped += 1
            continue

        features = data['features']
        # Filter city-level features (exclude province self-reference)
        city_features = []
        for feat in features:
            props = feat.get('properties', {})
            level = props.get('level', '')
            if level and level != 'province':
                if 'parent' not in props or not props['parent']:
                    props['parent'] = {'adcode': adcode}
                city_features.append(feat)

        all_features.extend(city_features)
        print(f'OK {len(city_features)} cities')

        # Polite delay
        time.sleep(0.3)

    print('-' * 50)
    print(f'Total: {len(all_features)} city features (skipped {skipped} provinces)')

    if not all_features:
        print('ERROR: No city data retrieved. Check network connection.')
        sys.exit(1)

    # Build FeatureCollection
    result = {
        'type': 'FeatureCollection',
        'features': all_features,
        '_meta': {
            'source': 'DataV.GeoAtlas',
            'feature_count': len(all_features),
            'description': 'China prefecture-level city boundaries (merged)'
        }
    }

    # Write file
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)

    file_size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f'\nSaved to: {OUTPUT_PATH}')
    print(f'  File size: {file_size_mb:.1f} MB')
    print(f'  Features: {len(all_features)}')


if __name__ == '__main__':
    main()
