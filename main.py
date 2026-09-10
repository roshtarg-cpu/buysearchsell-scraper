"""
BuySearchSell.com.au Scraper - Extract classified ads from BuySearchSell Australia
"""

from apify import Actor
from playwright.async_api import async_playwright
from datetime import datetime

async def main():
    async with Actor:
        # Get input
        actor_input = await Actor.get_input() or {}
        max_results = actor_input.get('maxResults', 100)
        start_url = actor_input.get('startUrl', 'https://www.buysearchsell.com.au/all-locations/trades-services/')
        
        Actor.log.info(f'Starting BuySearchSell scraper')
        Actor.log.info(f'URL: {start_url}')
        Actor.log.info(f'Max results: {max_results}')
        
        results = []
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                # Navigate to category page
                Actor.log.info(f'Navigating to {start_url}')
                await page.goto(start_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Extract listings from the page
                Actor.log.info('Extracting listings...')
                listings = await page.evaluate('''() => {
                    const items = [];
                    
                    // Find all listing containers
                    const containers = document.querySelectorAll('.span2.item, .item, div[data-overlay-marker]');
                    
                    containers.forEach(container => {
                        try {
                            // Get the main link
                            const link = container.querySelector('a[href*="/trades-services/"], a[href*="/buy-sell/"], a[href*="/notices/"]');
                            if (!link || !link.href) return;
                            
                            // Skip if not a listing URL (must have ID at end)
                            if (!/\\/\\d+\\/?$/.test(link.href)) return;
                            
                            const url = link.href;
                            
                            // Extract ID
                            const idMatch = url.match(/\\/(\\d+)\\/?$/);
                            const id = idMatch ? idMatch[1] : null;
                            
                            // Get title
                            const titleEl = container.querySelector('h3, h2, h4');
                            const title = titleEl ? titleEl.textContent.trim() : null;
                            
                            // Get image
                            const imgEl = container.querySelector('img');
                            const image = imgEl ? imgEl.src : null;
                            
                            // Extract category from URL
                            const parts = url.split('/').filter(p => p);
                            const category = parts.length > 1 ? parts[parts.length - 4] : null;
                            const subcategory = parts.length > 2 ? parts[parts.length - 3] : null;
                            
                            if (title && url && id) {
                                items.push({
                                    id: id,
                                    title: title,
                                    url: url,
                                    category: category ? category.replace(/-/g, ' ') : null,
                                    subcategory: subcategory ? subcategory.replace(/-/g, ' ') : null,
                                    image: image
                                });
                            }
                        } catch (err) {
                            console.error('Error processing item:', err);
                        }
                    });
                    
                    return items;
                }''')
                
                Actor.log.info(f'Found {len(listings)} listings on page')
                
                # Process each listing
                for idx, listing in enumerate(listings[:max_results]):
                    try:
                        Actor.log.info(f'Processing {idx+1}/{min(len(listings), max_results)}: {listing["title"]}')
                        
                        # Visit detail page
                        detail_page = await context.new_page()
                        await detail_page.goto(listing['url'], wait_until='domcontentloaded', timeout=20000)
                        await detail_page.wait_for_timeout(1500)
                        
                        # Extract details from the page
                        details = await detail_page.evaluate('''() => {
                            const data = {};
                            
                            // Try to find description
                            const descEl = document.querySelector('.ad-description, .description, .content, [class*="description"]');
                            data.description = descEl ? descEl.textContent.trim() : null;
                            
                            // Location
                            const locEl = document.querySelector('.location, [class*="location"]');
                            data.location = locEl ? locEl.textContent.trim() : null;
                            
                            // Price
                            const priceEl = document.querySelector('.price, [class*="price"]');
                            data.price = priceEl ? priceEl.textContent.trim() : null;
                            
                            // Phone
                            const phoneEl = document.querySelector('a[href^="tel:"], .phone, [class*="phone"]');
                            data.phone = phoneEl ? phoneEl.textContent.trim() : null;
                            
                            // Email
                            const emailEl = document.querySelector('a[href^="mailto:"], .email');
                            data.email = emailEl ? emailEl.textContent.trim() : null;
                            
                            return data;
                        }''')
                        
                        await detail_page.close()
                        
                        # Merge data
                        result = {
                            **listing,
                            **details,
                            'scrapedAt': datetime.utcnow().isoformat() + 'Z'
                        }
                        
                        # Push to dataset
                        await Actor.push_data(result)
                        results.append(result)
                        
                        Actor.log.info(f'✅ Saved: {result["title"]}')
                        
                        if len(results) >= max_results:
                            break
                            
                    except Exception as e:
                        Actor.log.error(f'Error processing {listing.get("title", "unknown")}: {e}')
                        continue
                
            except Exception as e:
                Actor.log.error(f'Fatal error: {e}')
                raise
            finally:
                await browser.close()
        
        Actor.log.info(f'✅ Scraping completed. Total: {len(results)} items')
