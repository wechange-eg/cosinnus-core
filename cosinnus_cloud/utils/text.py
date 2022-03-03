
def utf8_encode(s):
    return s if isinstance(s, bytes) else s.encode('utf8')
