import requests
import json
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urlparse, urljoin

class BlogScraper:
    def __init__(self, base_url, output_dir="blog_posts"):
        self.base_url = base_url
        self.output_dir = os.path.abspath(output_dir)
        self.session = requests.Session()
        self.visited_urls = set()
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Saving files to: {self.output_dir}")
        
        # Set up session headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def clean_filename(self, url):
        """Create a clean filename from URL"""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if not path:
            return 'index.html'
        
        # Remove problematic characters and ensure .html extension
        filename = path.replace('/', '_')
        if not filename.endswith('.html'):
            filename = filename.replace('.html', '') + '.html'
        
        # Replace any remaining problematic characters
        for char in ['\\', ':', '*', '?', '"', '<', '>', '|']:
            filename = filename.replace(char, '_')
        
        return filename

    def fix_url(self, url):
        """Fix URL to match the correct blog structure"""
        if not url.startswith(self.base_url):
            return url
            
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        # Skip if it's already correct or is a special URL
        if path.startswith('general/') or path in ['', 'index.html'] or \
           any(path.startswith(x) for x in ['categories/', 'images/', 'discord.', 'twitter.']):
            return url
            
        # Add 'general/' to the path for blog posts
        if path.count('/') >= 2:  # Looks like a blog post URL
            parts = path.split('/')
            new_path = f'general/{"/".join(parts)}'
            return f"{self.base_url}/{new_path}"
            
        return url

    def save_content(self, url, content):
        """Save content to HTML file"""
        try:
            filename = self.clean_filename(url)
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)
            
            file_size = os.path.getsize(filepath)
            print(f"Saved {url} to {filepath} (Size: {file_size} bytes)")
            return filepath
            
        except Exception as e:
            print(f"Error saving {url}: {str(e)}")
            return None

    def modify_html_content(self, html_content, url):
        """Add styling and modify HTML content"""
        if not html_content:
            print(f"Empty content received for {url}")
            return None
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Create new HTML structure
            new_html = BeautifulSoup('<!DOCTYPE html><html><head></head><body></body></html>', 'html.parser')
            
            # Move content to new structure
            new_html.body.append(soup)
            
            # Add style tag
            style = new_html.new_tag('style')
            style.string = """
                body { 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px; 
                    font-family: Arial, sans-serif; 
                    line-height: 1.6;
                    color: #333;
                }
                img { max-width: 100%; height: auto; }
                pre { 
                    background-color: #f5f5f5; 
                    padding: 15px; 
                    overflow-x: auto;
                    border-radius: 4px;
                }
                code { 
                    background-color: #f5f5f5; 
                    padding: 2px 5px;
                    border-radius: 3px;
                }
                h1, h2, h3 { color: #2c3e50; }
                a { color: #3498db; }
                blockquote {
                    border-left: 4px solid #ccc;
                    margin: 0;
                    padding-left: 16px;
                } 
            """
            new_html.head.append(style)
            
            # Add source URL as a reference
            source_div = new_html.new_tag('div')
            source_div['style'] = 'margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666;'
            source_div.string = f"Source: {url}"
            new_html.body.append(source_div)
            
            return str(new_html)
            
        except Exception as e:
            print(f"Error modifying HTML for {url}: {str(e)}")
            return None

    def scrape_page(self, url):
        """Scrape a single page"""
        if url in self.visited_urls:
            return
        
        # Fix URL if needed
        url = self.fix_url(url)
        self.visited_urls.add(url)
        
        try:
            print(f"\nScraping {url}")
            response = self.session.get(url, timeout=30, allow_redirects=True)
            
            # Handle redirects
            if response.history:
                final_url = response.url
                if final_url != url:
                    print(f"Redirected to {final_url}")
                    if final_url in self.visited_urls:
                        return
                    self.visited_urls.add(final_url)
            
            if response.status_code == 404:
                print(f"Page not found: {url}")
                return
                
            response.raise_for_status()
            
            # Extract main content
            soup = BeautifulSoup(response.text, 'html.parser')
            main_content = soup.find('article') or soup.find('main') or soup.find('div', class_='post') or soup
            
            # Modify and save the HTML content
            modified_html = self.modify_html_content(str(main_content), url)
            if modified_html:
                self.save_content(url, modified_html)
            
            # Add delay between requests
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {str(e)}")
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")

    def process_links(self, links_data):
        """Process all links from the JSON data"""
        # Get unique URLs from the links data
        unique_urls = set()
        for source_url, target_urls in links_data['links'].items():
            if source_url.startswith(self.base_url):
                unique_urls.add(source_url)
            for target_url in target_urls:
                if target_url.startswith(self.base_url):
                    unique_urls.add(target_url)
        
        # Remove URLs that are clearly not blog posts
        unique_urls = {url for url in unique_urls 
                      if not url.endswith(('jpg', 'png', 'gif', 'pdf', 'zip'))}
        
        total_links = len(unique_urls)
        processed = 0
        
        print(f"\nFound {total_links} unique URLs to process")
        
        try:
            for url in sorted(unique_urls):
                self.scrape_page(url)
                processed += 1
                print(f"Progress: {processed}/{total_links} ({(processed/total_links)*100:.2f}%)")
                
        except KeyboardInterrupt:
            print("\nScraping interrupted by user. Progress saved.")
            return

def main():
    try:
        # Load the JSON data
        with open('internal_links.json', 'r', encoding='utf-8') as f:
            links_data = json.load(f)
        
        # Initialize and run the scraper
        scraper = BlogScraper(base_url="https://vitalik.eth.limo")
        scraper.process_links(links_data)
        
        print("\nScraping completed! Check the blog_posts directory for the results.")
        
    except FileNotFoundError:
        print("Error: internal_links.json not found!")
    except json.JSONDecodeError:
        print("Error: invalid JSON format in internal_links.json!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()