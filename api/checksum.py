import io
import hashlib

def comp_checksum(args):
    """
    Compute MD5 Checksum

    :param : args<list> : list of strings/read buffer

    :returns : checksum<long>
    """
    g = io.BytesIO()
    for i in args:
        g.write(i)
    g.seek(0)
    s = g.read()
    m = hashlib.md5()
    m.update(s)
    cksum = m.hexdigest()
    g.close()
    return cksum
