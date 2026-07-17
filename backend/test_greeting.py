import asyncio
from app.configs.greetings import NOISE_TOKENS

def debug():
    t1_clean = "sujal"
    t2_clean = "singh"
    non_name_noise = NOISE_TOKENS
    print("t1 in noise:", t1_clean in non_name_noise)
    print("t2 in noise:", t2_clean in non_name_noise)

if __name__ == "__main__":
    debug()
