import time

def start_timer(duration_sec: int):
    return {"start": time.time(), "duration": duration_sec}

def remaining(timer_dict):
    if timer_dict is None:
        return 0
    
    try:
        start_time = timer_dict.get("start")
        duration = timer_dict.get("duration")
        
        if start_time is None or duration is None:
            return 0
            
        elapsed = time.time() - start_time
        return max(0, int(duration - elapsed))
    except Exception as e:
        print(f"Timer error: {str(e)}")
        return 0 