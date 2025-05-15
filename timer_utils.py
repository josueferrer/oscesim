import time

def start_timer(duration_sec: int):
    """
    Initialize a timer with specified duration in seconds.
    
    Args:
        duration_sec: Duration in seconds
        
    Returns:
        Dictionary with start time and duration
    """
    # Ensure duration is a valid integer
    if not isinstance(duration_sec, int) or duration_sec <= 0:
        duration_sec = 300  # Default to 5 minutes
        
    return {"start": time.time(), "duration": duration_sec}

def remaining(timer_dict):
    """
    Calculate remaining time in seconds.
    
    Args:
        timer_dict: Timer dictionary from start_timer
        
    Returns:
        Remaining seconds (int) or 0 if timer is invalid
    """
    if timer_dict is None:
        return 0
    
    try:
        # Ensure we have valid timer data
        start_time = timer_dict.get("start")
        duration = timer_dict.get("duration")
        
        # Handle missing or invalid data
        if not isinstance(start_time, (int, float)) or not isinstance(duration, (int, float)):
            return 0
            
        elapsed = time.time() - start_time
        return max(0, int(duration - elapsed))
    except Exception as e:
        print(f"Timer error: {str(e)}")
        return 0 