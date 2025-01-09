import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from typing import Set, Dict
import time

class WebsiteCrawler:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.visited_urls: Set[str] = set()
        self.internal_links: Dict[str, list] = {}
        self.session = requests.Session()
        # Add headers to mimic a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def is_internal_link(self, url: str) -> bool:
        """Check if the URL belongs to the same domain."""
        return self.domain in url

    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and adding scheme if missing."""
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)
        return url.split('#')[0].rstrip('/')

    def extract_links(self, url: str) -> Set[str]:
        """Extract all links from a given URL."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = set()
            for anchor in soup.find_all('a', href=True):
                href = anchor.get('href')
                normalized_url = self.normalize_url(href)
                if self.is_internal_link(normalized_url):
                    links.add(normalized_url)
            
            return links
        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
            return set()

    def crawl(self):
        """Crawl the website and collect all internal links."""
        urls_to_visit = {self.base_url}

        while urls_to_visit:
            current_url = urls_to_visit.pop()
            if current_url in self.visited_urls:
                continue

            print(f"Crawling: {current_url}")
            found_links = self.extract_links(current_url)
            self.internal_links[current_url] = list(found_links)
            self.visited_urls.add(current_url)
            
            # Add new internal links to visit
            urls_to_visit.update(found_links - self.visited_urls)
            
            # Be nice to the server
            time.sleep(1)

    def save_to_json(self, filename: str = 'internal_links.json'):
        """Save the collected links to a JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'base_url': self.base_url,
                'total_pages': len(self.internal_links),
                'links': self.internal_links
            }, f, indent=2, ensure_ascii=False)

def main():
    base_url = "https://vitalik.eth.limo"
    crawler = WebsiteCrawler(base_url)
    crawler.crawl()
    crawler.save_to_json()
    print(f"Crawling completed. Found {len(crawler.internal_links)} pages.")

if __name__ == "__main__":
    main()