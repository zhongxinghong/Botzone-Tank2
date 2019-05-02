# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-02 04:41:21
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-02 05:44:33

import base64
import pickle
import zlib


def b(s):
    """
    bytes/str/int/float -> bytes
    """
    if isinstance(s, bytes):
        return s
    elif isinstance(s, (str,int,float)):
        return str(s).encode("utf-8")
    else:
        raise TypeError(s)

def u(s):
    """
    bytes/str/int/float -> str(utf8)
    """
    if isinstance(s, (str,int,float)):
        return str(s)
    elif isinstance(s, bytes):
        return s.decode("utf-8")
    else:
        raise TypeError(s)

data = {

    "status": [1,2,4,5,7,3,],
    "aslfja": {"123",123,43,"af",(2,55,6)},
    "adfs": "adsjflka",
    "jadldsaf": [23, "adfs"]
}


class DataSerializer(object):

    @staticmethod
    def _unpad(s):
        return s.rstrip("=")

    @staticmethod
    def _pad(s):
        return s + "=" * ( 4 - len(s) % 4 )

    @staticmethod
    def serialize(obj):
        return __class__._unpad(
                    base64.b64encode(
                        zlib.compress(
                            pickle.dumps(obj))).decode("utf-8"))

    @staticmethod
    def deserialize(s):
        return pickle.loads(
                    zlib.decompress(
                        base64.b64decode(
                            __class__._pad(s).encode("utf-8"))))


a = DataSerializer.serialize(data)

print(a)
print(len(a) / 4)

b = DataSerializer.deserialize(a)

print(b)