"""
BuySearchSell.com.au Scraper - Extract classified ads from BuySearchSell Australia
"""

from apify import Actor
from playwright.async_api import async_playwright
import re

async def main():
    async with Actor:
        # Get input
        actor_input = await Actor.get_input() or {}
        max_results = actor_input.get('maxResults', 100)
        start_url = actor_input.get('startUrl', 'https://www.buysearchsell.com.au/all-locations/trades-services/')
        
        Actor.log.info(f'Starting BuySearchSell scraper with max_results={max_results}')
        Actor.log.info(f'Start URL: {start_url}')
        
        results = []
        
        async with async_playwright() as playwright:
            # Launch browser
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                # Navigate to the category page
                Actor.log.info(f'Navigating to {start_url}')
                await page.goto(start_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)  # Wait for dynamic content
                
                # Extract listings
                listings = await page.evaluate('''() => {
                    const items = [];
                    
                    // Find all listing containers
                    const containers = document.querySelectorAll('.span2.item, .container-section-vertical-item');
                    
                    containers.forEach(container => {
                        try {
                            // Get link
                            const link = container.querySelector('a[href*="/trades-services/"], a[href*="/buy-sell/"], a[href*="/notices/"], a[href*="/adult-services/"]');
                            if (!link) return;
                            
                            const url = link.href;
                            
                            // Extract ID from URL (last number before trailing slash)
                            const idMatch = url.match(/\\/([0-9]+)\\/?$/);
                            const id = idMatch ? idMatch[1] : null;
                            
                            // Get title
                            const titleEl = container.querySelector('h3 a, h2 a, .item-details a');
                            const title = titleEl ? titleEl.textContent.trim() : null;
                            
                            // Get image
                            const imgEl = container.querySelector('img');
                            const image = imgEl ? imgEl.src : null;
                            
                            // Get category from URL
                            const categoryMatch = url.match(/\\/([^\\/]+)\\/([^\\/]+)\\/[^\\/]+\\/[0-9]+/);
                            const category = categoryMatch ? categoryMatch[1].replace(/-/g, ' ') : null;
                            const subcategory = categoryMatch ? categoryMatch[2].replace(/-/g, ' ') : null;
                            
                            if (title && url && id) {
                                items.push({
                                    id: id,
                                    title: title,
                                    url: url,
                                    category: category,
                                    subcategory: subcategory,
                                    image: image
                                });
                            }
                        } catch (err) {
                            console.error('Error processing item:', err);
                        }
                    });
                    
                    return items;
                }''')
                
                Actor.log.info(f'Extracted {len(listings)} listings from category page')
                
                # Process each listing (optionally visit detail pages)
                for listing in listings[:max_results]:
                    try:
                        # Visit detail page to get more info
                        Actor.log.info(f'Processing: {listing["title"]} ({listing["id"]})')
                        
                        detail_page = await context.new_page()
                        await detail_page.goto(listing['url'], wait_until='domcontentloaded', timeout=20000)
                        await detail_page.wait_for_timeout(1000)
                        
                        # Extract details
                        details = await detail_page.evaluate('''() => {
                            const data = {};
                            
                            // Description
                            const descEl = document.querySelector('.ad-description, .description, .content p');
                            data.description = descEl ? descEl.textContent.trim() : null;
                            
                            // Location
                            const locEl = document.querySelector('.location, [class*="location"]');
                            data.location = locEl ? locEl.textContent.trim() : null;
                            
                            // Price
                            const priceEl = document.querySelector('.price, [class*="price"]');
                            data.price = priceEl ? priceEl.textContent.trim() : null;
                            
                            // Contact info
                            const phoneEl = document.querySelector('[href^="tel:"], .phone');
                            data.phone = phoneEl ? phoneEl.textContent.trim() : null;
                            
                            const emailEl = document.querySelector('[href^="mailto:"], .email');
                            data.email = emailEl ? emailEl.textContent.trim() : null;
                            
                            return data;
                        }''')
                        
                        await detail_page.close()
                        
                        # Merge listing and details
                        from datetime import datetime
                        result = {
                            **listing,
                            **details,
                            'scrapedAt': datetime.utcnow().isoformat() + 'Z'
                        }
                        
                        # Push to dataset
                        await Actor.push_data(result)
                        results.append(result)
                        
                        Actor.log.info(f'Saved: {result["title"]}')
                        
                        if len(results) >= max_results:
                            Actor.log.info(f'Reached max_results limit: {max_results}')
                            break
                            
                    except Exception as e:
                        Actor.log.error(f'Error processing listing {listing["id"]}: {e}')
                        continue
                
            except Exception as e:
                Actor.log.error(f'Error during scraping: {e}')
                raise
            finally:
                await browser.close()
        
        Actor.log.info(f'Scraping completed. Total items: {len(results)}')
