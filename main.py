"""
BuySearchSell.com.au Scraper
"""

from apify import Actor
from playwright.async_api import async_playwright
from datetime import datetime

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        max_results = actor_input.get('maxResults', 100)
        start_url = actor_input.get('startUrl', 'https://www.buysearchsell.com.au/all-locations/trades-services/')
        
        Actor.log.info(f'Starting scraper with max_results={max_results}')
        
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                Actor.log.info(f'Loading {start_url}')
                await page.goto(start_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
                
                # Get all listing links
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a[href*="/trades-services/"]'))
                        .map(a => a.href)
                        .filter(url => /\\/\\d+\\/?$/.test(url))
                        .slice(0, 50);
                }''')
                
                Actor.log.info(f'Found {len(links)} listing URLs')
                
                count = 0
                for url in links[:max_results]:
                    try:
                        Actor.log.info(f'Scraping {url}')
                        await page.goto(url, wait_until='domcontentloaded')
                        await page.wait_for_timeout(1000)
                        
                        # Extract data
                        data = await page.evaluate('''() => {
                            const title = document.querySelector('h1, h2')?.textContent?.trim() || 'N/A';
                            const desc = document.querySelector('.description, .content')?.textContent?.trim() || '';
                            return {
                                title,
                                description: desc.substring(0, 500),
                                url: window.location.href
                            };
                        }''')
                        
                        data['scrapedAt'] = datetime.utcnow().isoformat() + 'Z'
                        
                        await Actor.push_data(data)
                        count += 1
                        Actor.log.info(f'✅ Saved {count}/{max_results}')
                        
                        if count >= max_results:
                            break
                    except Exception as e:
                        Actor.log.error(f'Error on {url}: {e}')
                        continue
                        
            finally:
                await browser.close()
        
        Actor.log.info(f'Done. Scraped {count} items')

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
