from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from kernel.orchestrator.models import ExecutionContext

@dataclass
class TemporalResolution:
    time_min: str
    time_max: str

class TemporalResolver:
    """Translates semantic date ranges into exact ISO-8601 boundaries."""
    
    @staticmethod
    def resolve(date_range: str, ctx: ExecutionContext) -> TemporalResolution | None:
        """Resolve a semantic date range into a TemporalResolution."""
        if not date_range:
            return None
            
        range_lower = date_range.strip().lower()
        
        # We work with timezone-aware datetime directly from ctx.now
        now = ctx.now
        
        # Helpful start/end of current day
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        if range_lower == "today":
            return TemporalResolution(
                time_min=today_start.isoformat(),
                time_max=today_end.isoformat()
            )
            
        if range_lower == "tomorrow":
            tomorrow_start = today_start + timedelta(days=1)
            tomorrow_end = today_end + timedelta(days=1)
            return TemporalResolution(
                time_min=tomorrow_start.isoformat(),
                time_max=tomorrow_end.isoformat()
            )
            
        if range_lower == "yesterday":
            yesterday_start = today_start - timedelta(days=1)
            yesterday_end = today_end - timedelta(days=1)
            return TemporalResolution(
                time_min=yesterday_start.isoformat(),
                time_max=yesterday_end.isoformat()
            )
            
        if range_lower == "this_week":
            # Assistant logic: people usually mean "from today until Sunday"
            # If today is already Sunday, they usually mean the new week (next 7 days)
            days_to_sunday = 6 - today_start.weekday()
            if days_to_sunday == 0:
                end_of_week = today_end + timedelta(days=6)
            else:
                end_of_week = today_end + timedelta(days=days_to_sunday)
                
            return TemporalResolution(
                time_min=today_start.isoformat(),
                time_max=end_of_week.isoformat()
            )
            
        if range_lower == "next_week":
            start_of_next_week = today_start + timedelta(days=7 - today_start.weekday())
            end_of_next_week = today_end + timedelta(days=13 - today_start.weekday())
            return TemporalResolution(
                time_min=start_of_next_week.isoformat(),
                time_max=end_of_next_week.isoformat()
            )
            
        if range_lower == "last_week":
            start_of_last_week = today_start - timedelta(days=today_start.weekday() + 7)
            end_of_last_week = today_end - timedelta(days=today_start.weekday() + 1)
            return TemporalResolution(
                time_min=start_of_last_week.isoformat(),
                time_max=end_of_last_week.isoformat()
            )
            
        # Optional: Add month logic if needed, or fallback to None for complex ones
        
        return None
