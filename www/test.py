#!/user/bin/env python3
# -*- coding: utf-8 -*-

import sys,asyncio
from www.orm import create_pool,destory_pool
from www.models import User,Blog,Comment

@asyncio.coroutine
def test( loop ):
    yield from create_pool( loop = loop, user='root', password='123', db='test' )
    u = User(name='aaa', email='aaa@qq.com', passwd='aaa', image='about:blank')
    yield from u.save()
#    r = yield from u.findAll()
#    print(r)
    yield from destory_pool()

if __name__ == '__main__':

    loop = asyncio.get_event_loop()
    loop.run_until_complete( asyncio.wait([test( loop )]) )
    loop.close()
    if loop.is_closed():
        sys.exit(0)