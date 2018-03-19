class APIError(Exception):
	'''
	APIError基类， 包含错误类型（必要），数据（可选），信息（可选）
	'''
	def __init__(self, error, data = '', message = ''):
		super(APIError, self).__init__(message)
		self.error = error
		self.data = data
		self.message = message

class APIValueError(APIError):
	'''
	数据输入有问题，data说明输入的错误字段
	'''
	def __init__(self, field, message = ''):
		super(APIValueError, self).__init__('Value: invalid', field, message)

class APIResourceNotfoundError(APIError):
	# 找不到资源
	def __init__(self, field, message = ''):
		super(APIResourceNotfoundError,self).__init__('Value: Notfound', field, message)

class APIPermissionError(APIError):
	# 没有接口权限
	def __init__(self, message = ''):
		super(APIPermissionError, self).__init__('Permission: forbidden', 'Permission', message)
