
from www.coreweb import  get,post

# 主页
@get('/')
async def index(request, *, page='1'):
	return 'index'
