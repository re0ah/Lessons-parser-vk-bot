import json
import os

FNAME = "list.json"

"""store dict elements as: {vk_id: course}"""
data = {}

def init():
	"""create students list file if not exist"""
	if os.path.exists(FNAME):
		load()
		return
	save()

def save():
	"""save students list file"""
	global data
	with open(FNAME, "w") as fp:
		json.dump(data, fp)

def load():
	"""return json from students list file"""
	global data
	with open(FNAME, "r") as fp:
		data = json.load(fp)

def append(user_id, group_name):
	global data
	data[str(user_id)] = group_name
	save()

init()
