import asyncio
import logging

logger = logging.getLogger(__name__)

async def get_trending_topics(
    config: dict,
    fallback_topics: list[str]
) -> list[str]:
    """Fetch trending tech topics from Google Trends.
    
    Returns a list of trending topic strings to add to 
    the topic pool for today's generation run.
    Falls back silently to empty list on any failure.
    """
    try:
        from pytrends.request import TrendReq
        
        loop = asyncio.get_event_loop()
        
        def fetch_trends():
            pytrends = TrendReq(hl='en-US', tz=330)  # IST timezone
            
            # Search for trending topics in tech category
            pytrends.build_payload(
                kw_list=['technology', 'AI', 'programming'],
                cat=0,
                timeframe='now 1-d',  # last 24 hours
                geo='IN'  # India
            )
            
            related = pytrends.related_queries()
            
            topics = []
            for kw in ['technology', 'AI', 'programming']:
                df = related.get(kw, {}).get('top')
                if df is not None and not df.empty:
                    topics.extend(df['query'].tolist()[:5])
            
            return topics[:10]  # max 10 trending topics
        
        trending = await loop.run_in_executor(None, fetch_trends)
        
        if trending:
            logger.info(
                f"[trends] Found {len(trending)} trending topics"
            )
            return trending
        else:
            logger.info("[trends] No trending topics found — using config list")
            return []
            
    except Exception as e:
        logger.warning(f"[trends] pytrends failed: {e} — using config list")
        return []
