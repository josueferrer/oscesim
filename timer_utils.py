import time

def start_timer(duration_sec: int):
    return {"start": time.time(), "duration": duration_sec}

def remaining(timer_dict):
    elapsed = time.time() - timer_dict["start"]
    return max(0, int(timer_dict["duration"] - elapsed)) 