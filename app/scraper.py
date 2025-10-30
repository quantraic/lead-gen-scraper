import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import time

class WebsiteScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.timeout = 10
    
    def scrape_website(self, url):
        """
        Scrape a website for email and social media links
        Returns dict with email and social URLs
        """
        if not url:
            return None
        
        # Ensure URL has protocol
        if not url.startswith('http'):
            url = 'https://' + url
        
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract email and socials
            email = self.find_email(soup, response.text)
            socials = self.find_social_links(soup, url)
            
            return {
                'email': email,
                'facebook': socials.get('facebook', ''),
                'instagram': socials.get('instagram', ''),
                'linkedin': socials.get('linkedin', ''),
                'twitter': socials.get('twitter', '')
            }
            
        except requests.exceptions.Timeout:
            print(f"Timeout scraping {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error scraping {url}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error scraping {url}: {e}")
            return None
    
    def find_email(self, soup, text):
        """
        Find email addresses on the page
        Returns the first valid email found
        """
        # Common email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Search in text content
        emails = re.findall(email_pattern, text)
        
        # Filter out common false positives
        excluded_domains = ['example.com', 'yourdomain.com', 'email.com', 
                          'domain.com', 'sentry.io', 'wixpress.com']
        
        for email in emails:
            domain = email.split('@')[1].lower()
            if not any(excl in domain for excl in excluded_domains):
                return email
        
        # Also check mailto links
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
        for link in mailto_links:
            href = link.get('href', '')
            email_match = re.search(email_pattern, href)
            if email_match:
                return email_match.group(0)
        
        return ''
    
    def find_social_links(self, soup, base_url):
        """
        Find social media profile links
        Returns dict with social platform URLs
        """
        socials = {
            'facebook': '',
            'instagram': '',
            'linkedin': '',
            'twitter': ''
        }
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '').lower()
            
            # Make absolute URL
            absolute_url = urljoin(base_url, href)
            
            # Check for each social platform
            if 'facebook.com' in href and not socials['facebook']:
                # Extract clean Facebook URL
                if '/pages/' in href or '/profile.php' in href or re.search(r'facebook\.com/[^/\s]+', href):
                    socials['facebook'] = absolute_url.split('?')[0]  # Remove query params
            
            elif 'instagram.com' in href and not socials['instagram']:
                # Extract Instagram profile
                if re.search(r'instagram\.com/[^/\s]+', href):
                    socials['instagram'] = absolute_url.split('?')[0]
            
            elif 'linkedin.com' in href and not socials['linkedin']:
                # Extract LinkedIn profile or company page
                if '/company/' in href or '/in/' in href:
                    socials['linkedin'] = absolute_url.split('?')[0]
            
            elif ('twitter.com' in href or 'x.com' in href) and not socials['twitter']:
                # Extract Twitter/X profile
                if re.search(r'(twitter|x)\.com/[^/\s]+', href):
                    socials['twitter'] = absolute_url.split('?')[0]
        
        return socials
    
    def scrape_contact_page(self, base_url):
        """
        Try to find and scrape a contact page for better email results
        """
        if not base_url:
            return None
        
        if not base_url.startswith('http'):
            base_url = 'https://' + base_url
        
        # Common contact page URLs
        contact_paths = [
            '/contact',
            '/contact-us',
            '/about',
            '/about-us',
            '/get-in-touch'
        ]
        
        for path in contact_paths:
            try:
                contact_url = urljoin(base_url, path)
                response = requests.get(contact_url, headers=self.headers, timeout=5)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    email = self.find_email(soup, response.text)
                    if email:
                        return email
                        
            except:
                continue
        
        return None
    
    def scrape_batch(self, leads, delay=1):
        """
        Scrape multiple websites with rate limiting
        Updates leads list in place
        """
        total = len(leads)
        
        for idx, lead in enumerate(leads, 1):
            website = lead.get('website', '')
            
            if not website:
                continue
            
            print(f"Scraping {idx}/{total}: {website}")
            
            # Scrape main page
            scraped_data = self.scrape_website(website)
            
            if scraped_data:
                # Update lead with scraped data
                lead['email'] = scraped_data.get('email', '')
                lead['facebook'] = scraped_data.get('facebook', '')
                lead['instagram'] = scraped_data.get('instagram', '')
                lead['linkedin'] = scraped_data.get('linkedin', '')
                lead['twitter'] = scraped_data.get('twitter', '')
                
                # If no email found on main page, try contact page
                if not lead['email']:
                    contact_email = self.scrape_contact_page(website)
                    if contact_email:
                        lead['email'] = contact_email
            
            # Rate limiting - be respectful
            time.sleep(delay)
        
        return leads