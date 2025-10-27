#!/usr/bin/env python3
"""
Test script to download all 10-Q filings for NVIDIA (NVDA) from the last year.
This tests the complete SEC EDGAR scraping and document storage system.
"""

import asyncio
import logging
import sys
from pathlib import Path
import time

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.sec_edgar_scraper import SECEdgarScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def download_nvda_10q_filings():
    """Download all 10-Q filings for NVIDIA from the last year"""
    
    print("🚀 NVIDIA 10-Q Filings Download Test")
    print("=" * 60)
    
    # Target directory
    target_dir = Path("./data/documents/nvda")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    
    try:
        # Initialize SEC scraper
        async with SECEdgarScraper() as scraper:
            print("📡 Initializing SEC EDGAR scraper...")
            
            # Validate NVIDIA ticker
            is_valid, company_name, suggestions = await scraper.validate_ticker("NVDA")
            if not is_valid:
                print(f"❌ Invalid ticker NVDA. Suggestions: {suggestions}")
                return
            
            print(f"✅ Found company: {company_name}")
            
            # Get NVIDIA's CIK for verification
            cik = await scraper.get_company_cik("NVDA")
            print(f"📋 NVIDIA CIK: {cik}")
            
            # Get NVIDIA's 10-Q filings from the last year
            print("🔍 Searching for 10-Q filings in the last year...")
            filings = await scraper.scrape_filings(
                ticker="NVDA",
                years=1,  # Last 1 year
                filing_types=["10-Q"]  # Only 10-Q filings (quarterly reports)
            )
            
            if not filings:
                print("❌ No 10-Q filings found for NVDA in the last year")
                return
            
            print(f"📄 Found {len(filings)} 10-Q filings")
            
            # Sort filings by date (newest first)
            filings_sorted = sorted(filings, key=lambda f: f.filing_date, reverse=True)
            
            print(f"\n📋 10-Q Filings Found:")
            for i, filing in enumerate(filings_sorted):
                print(f"   {i+1:2d}. {filing.filing_date.strftime('%Y-%m-%d')} - {filing.accession_number}")
            
            # Download each filing
            print(f"\n⬇️  Starting download of {len(filings)} 10-Q filings...")
            print("-" * 60)
            
            downloaded_count = 0
            failed_count = 0
            total_size = 0
            
            for i, filing in enumerate(filings_sorted):
                print(f"\n📥 Downloading {i+1}/{len(filings)}: {filing.accession_number}")
                print(f"   📅 Filing Date: {filing.filing_date.strftime('%Y-%m-%d')}")
                print(f"   🔗 URL: {filing.document_url}")
                
                try:
                    # Create subdirectory for this filing
                    filing_dir = target_dir / filing.filing_date.strftime('%Y') / "10-Q"
                    filing_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Generate filename
                    filename = f"{filing.accession_number.replace('-', '')}.html"
                    local_file = filing_dir / filename
                    
                    # Skip if file already exists
                    if local_file.exists():
                        print(f"   ⏭️  File already exists: {local_file}")
                        downloaded_count += 1
                        total_size += local_file.stat().st_size
                        continue
                    
                    # Download the document
                    response = await scraper.client.get(filing.document_url)
                    response.raise_for_status()
                    
                    content = response.content
                    content_type = response.headers.get('content-type', 'text/html')
                    
                    # Save to file
                    with open(local_file, 'wb') as f:
                        f.write(content)
                    
                    file_size = len(content)
                    total_size += file_size
                    downloaded_count += 1
                    
                    print(f"   ✅ Downloaded: {file_size:,} bytes")
                    print(f"   💾 Saved to: {local_file}")
                    
                    # Rate limiting - be respectful to SEC servers
                    await asyncio.sleep(0.1)  # 100ms delay between downloads
                    
                except Exception as e:
                    failed_count += 1
                    print(f"   ❌ Failed to download: {e}")
                    continue
            
            # Summary
            elapsed_time = time.time() - start_time
            
            print(f"\n" + "=" * 60)
            print(f"📊 DOWNLOAD SUMMARY")
            print(f"=" * 60)
            print(f"✅ Successfully downloaded: {downloaded_count}/{len(filings)} filings")
            print(f"❌ Failed downloads: {failed_count}")
            print(f"📁 Target directory: {target_dir.absolute()}")
            print(f"💾 Total size downloaded: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
            print(f"⏱️  Total time: {elapsed_time:.2f} seconds")
            print(f"📈 Average speed: {(total_size/1024/1024)/elapsed_time:.2f} MB/s")
            
            # List all downloaded files
            print(f"\n📂 Downloaded Files Structure:")
            for file_path in sorted(target_dir.rglob("*.html")):
                relative_path = file_path.relative_to(target_dir)
                file_size = file_path.stat().st_size
                print(f"   📄 {relative_path} ({file_size:,} bytes)")
            
            # Verify file contents
            print(f"\n🔍 File Content Verification:")
            sample_files = list(target_dir.rglob("*.html"))[:2]  # Check first 2 files
            
            for file_path in sample_files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content_preview = f.read(500)
                        
                    print(f"\n📖 {file_path.name} (first 500 chars):")
                    print("-" * 40)
                    print(content_preview)
                    print("-" * 40)
                    
                    # Check if it looks like a valid SEC filing
                    if any(keyword in content_preview.lower() for keyword in ['nvidia', 'form 10-q', 'quarterly report', 'sec']):
                        print(f"   ✅ Content appears valid (contains expected keywords)")
                    else:
                        print(f"   ⚠️  Content may not be a valid SEC filing")
                        
                except Exception as e:
                    print(f"   ❌ Could not verify content: {e}")
    
    except Exception as e:
        logger.error(f"Error downloading NVDA 10-Q filings: {e}")
        print(f"❌ Error: {e}")
        raise


async def main():
    """Main function"""
    try:
        await download_nvda_10q_filings()
        print("\n🎉 NVIDIA 10-Q download test completed successfully!")
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())