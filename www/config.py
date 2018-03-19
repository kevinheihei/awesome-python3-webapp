#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Configuration
'''


from www import config_default


class Dict(dict):
    """
    重写属性设置，获取方法
    支持通过属性名访问键值对的值，属性名将被当做键名
    """
    def __init__(self, names=(), values=(), **kw):
        super().__init__(**kw)
        # zip函数将参数数据分组返回[(arg1[0],arg2[0],arg3[0]...),(arg1[1],arg2[1],arg3[1]...),,,]
        # 以参数中元素数量最少的集合长度为返回列表长度
        for k, v in zip(names, values):  #zip 返回元祖列表
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute like '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value


def merge(defaults, override):
    r = {}
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])  # 若v是dict，继续迭代
            else:
                r[k] = override[k]  # 否则，用新值覆盖默认值
        else:
            r[k] = v  # 覆盖参数未定义时，仍使用默认参数
    return r


def toDict(configs):
    D = Dict()
    for k, v in configs.items():
        # 使用三目运算符，如果值是一个dict递归将其转换为Dict再赋值，否则直接赋值
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D


configs = config_default.configs
try:
    import config_override

    configs = merge(configs, config_override.configs)  # 获得组合后的configs，dict
except ImportError:
    pass
configs = toDict(configs)  # 将configs组合成Dict类的实例，可以通过configs.k直接获取v

