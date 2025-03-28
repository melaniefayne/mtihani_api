import string, random

def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))