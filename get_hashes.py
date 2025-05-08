import requests
import re
import json

JS_BUNDLE_URL = "https://abs.twimg.com/responsive-web/client-web/main.8f570f4a.js"

def fetch_graphql_hashes_from_js(js_url):
    print(f"Fetching JS bundle: {js_url}")
    resp = requests.get(js_url)
    resp.raise_for_status()
    js_code = resp.text

    # Find all queryId + operationName pairs
    matches = re.findall(r'queryId:"(\w+)",operationName:"(\w+)"', js_code)
    graphql_map = {op: qid for qid, op in matches}

    # Save to file
    with open("graphql_hashes.json", "w") as f:
        json.dump(graphql_map, f, indent=2)

    print(f"Found {len(graphql_map)} GraphQL operations:")
    for op in sorted(graphql_map.keys())[:10]:  # preview first 10
        print(f"{op}: {graphql_map[op]}")

    return graphql_map

if __name__ == "__main__":
    fetch_graphql_hashes_from_js(JS_BUNDLE_URL)
