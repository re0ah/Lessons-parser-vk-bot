import vk_api, random
import urllib.request
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from threading import Thread
import mailing_list

class Update_lesson_th(Thread):
	"""Поток для обновления данных о том, какие пары на текущей неделе.
	   Раз в n секунд проверяет, были ли изменены списки пар и обновляет
	   их в случае изменения"""
	def __init__(self, days_info):
		super().__init__()
		self.days_info = days_info

	def run(self):
		while True:
			time.sleep(300)
			self.if_lesson_changed()

	def if_lesson_changed(self):
		days_info_check = Days_info()
		if days_info_check.server_status == False:
			print("Сервер недоступен для проверки изменения расписания. Запросы\
				   к боту будут возвращать то расписание, что было во время\
				   удачной проверки. Ожидание 300 секунд.")
			return
		days_info_check.init_ready_loop() #ожидание окончания парсинга
		if self.days_info.data == days_info_check.data:
			print("Расписание не изменилось")
		else:
			print("Расписание изменено")
			self.days_info.data = days_info_check.data

class Init_days_info_th(Thread):
	"""Поток для парсинга данных о расписании одного из дней"""
	def __init__(self, weekday, days_info):
		super().__init__()
		self.days_info = days_info
		self.weekday = weekday
		self.ready = False

	def run(self):
		self.days_info.update_info(self.weekday)
		self.ready = True

class Days_info():
	"""Хранит данные, что были спарсены с сайта:
	   1. Список групп
	   2. Список пар этих групп для каждого из дней недели"""
	data = []
	def __init__(self):
		self.server_status = True
		try:
			with urllib.request.urlopen(f"https://xn--c1akimkh.xn--p1ai") as url:
				pass
		except:
			self.server_status = False
			return
		self.data = [None, None, None, None, None, None, None]
		self.soup = [None, None, None, None, None, None, None]
		self.init_threads = []
		for i in range(1, 6):
			self.init_threads.append(Init_days_info_th(i, self))
			self.init_threads[i - 1].start()
	
	def init_ready_loop(self):
		while(True):
			ready = True
			for i in range(len(self.init_threads)):
				ready &= self.init_threads[i].ready
			if ready:
			 	break
			time.sleep(0.05)
	
	def update_info(self, day):
		groups = []
		groups_lesson = {}
		with urllib.request.urlopen(f"https://xn--c1akimkh.xn--p1ai/lesson_table_show/?day={day}") as url:
			soup = BeautifulSoup(url.read(), "lxml")
			self.parse(groups, groups_lesson, soup, day)
			self.data[day - 1] = {"groups": groups,
								  "groups_lesson": groups_lesson}

	def lesson_list(self, day, group_name, id_html, soup):
		lesson_list_str = ""
		for i in range(1, 10):
			lesson_list_str += soup.find(id=f"{id_html}_{i}").getText() + '\n'
		return lesson_list_str[:-1]

	def parse(self, groups, groups_lesson, soup, day):
		tables = soup.find_all("th")
		for i in tables:
			group_name = i.getText()
			groups.append(group_name)
			groups_lesson[group_name] = self.lesson_list(day, group_name, i.get("id"), soup)

	def __getitem__(self, key):
		return self.data[key]

class Mailing_th(Thread):
	"""Поток для рассылки расписания"""
	def __init__(self, vk):
		super().__init__()
		self.vk = vk

	def run(self):
		while True:
			now = datetime.now()
			time.sleep(self.calc_sleep_time())
			if now.weekday() == 6:
				weekday = -1
			for user_id in list(mailing_list.data.keys()):
				lessons_list = days_info[now.weekday() + 1]["groups_lesson"][mailing_list.data[str(user_id)]]
				vk.method('messages.send',{'user_id': user_id,'message': "Расписание на завтра:\n\n" + lessons_list, 'random_id':random.randint(1,2147483647)})
	
	def calc_sleep_time(self):
		now = datetime.now()
		now_18h = now.replace(hour=18, minute=0, second=0)
		diff = now_18h - now
		diff_in_sec = diff.total_seconds()
		if diff_in_sec < 0:
			diff_in_sec += 86400
		if now.weekday() == 4:
			diff_in_sec += 86400
		if now.weekday() == 5:
			diff_in_sec += 86400
		return diff_in_sec

class Groups_info():
	def __init__(self, groups):
		self.groups = groups
		
		self.spec_lst = []
		self.spec_groups = {}
		self.groups_with_days = {}
		self.mailing_spec_lst = []
		self.mailing_spec_to_spec = {}
		self.mailing_groups_to_groups = {}
		for i in self.groups:
			self.groups_with_days[f"ПН_{i}"] = (0, i)
			self.groups_with_days[f"ВТ_{i}"] = (1, i)
			self.groups_with_days[f"СР_{i}"] = (2, i)
			self.groups_with_days[f"ЧТ_{i}"] = (3, i)
			self.groups_with_days[f"ПТ_{i}"] = (4, i)

			self.mailing_groups_to_groups[f"{i}."] = i
			spec_name = i.split(' ')[0]
			if spec_name in self.spec_lst:
				self.spec_groups[spec_name].append(i)
				continue
			self.mailing_spec_lst.append(f"{spec_name}.")
			self.mailing_spec_to_spec[f"{spec_name}."] = spec_name
			self.spec_lst.append(spec_name)
			self.spec_groups[spec_name] = [i]
		print("spec_lst: ", self.spec_lst)
		print("spec_groups: ", self.spec_groups)
		print("groups_with_days, ", self.groups_with_days)
		print("mailing_spec_lst", self.mailing_spec_lst)
		print("mailing_spec_to_spec", self.mailing_spec_to_spec)
		print("mailing_groups_to_groups", self.mailing_groups_to_groups)

class Vk_btns():
	def __init__(self):
		self.kbd_all = self.make_kbd(3,
									 gr_info.spec_lst + ["Подписка на рассылку", "Инфо"],
									 ["primary", "primary", "negative",
									 "negative", "negative", "negative", 
									 "positive", "positive", "positive",
									 "default", "default"],
									 back_btn=False)

		self.kbd_get_mailing = self.make_kbd(3,
											 gr_info.mailing_spec_lst,
											 ["primary", "primary", "negative",
											 "negative", "negative", "negative", 
											 "positive", "positive", "positive"],
											 back_btn=False)
		self.kbd_mailing = {}
		for i in gr_info.spec_lst:
			self.kbd_mailing[i] = self.make_kbd(2,
									 		 [f"{x}." for x in gr_info.spec_groups[i]],
									 		 ["primary" for x in gr_info.spec_groups[i]],
									 		 back_btn=True)

		self.kbd_days = {}
		for i in gr_info.spec_lst:
			for j in gr_info.spec_groups[i]:
				self.kbd_days[j] = self.make_kbd_day(j)

		self.kbd_groups = {}
		for i in gr_info.spec_lst:
			self.kbd_groups[i] = self.make_kbd(2,
									 		   gr_info.spec_groups[i],
									 		   ["primary" for x in gr_info.spec_groups[i]],
									 		   back_btn=True)

	def make_btn(self, label, color, payload = []):
		return {
			"action": 
			{
				"type": "text",
				"payload": json.dumps(payload),
				"label": label
			},
			"color": color
		}

	def make_kbd(self, width=2, lbls=[], colors=[], back_btn=False):
		ret = {"one_time": False,
			   "buttons": [[]]
		}
		lst_now = 0
		for i in range(len(lbls)):
			if len(ret["buttons"][lst_now]) != width:
				ret["buttons"][lst_now].append(self.make_btn(lbls[i], colors[i]))
			else:
				lst_now += 1
				ret["buttons"].append([])
				ret["buttons"][lst_now].append(self.make_btn(lbls[i], colors[i]))
		if back_btn:
			if len(ret["buttons"][lst_now]) == width:
				ret["buttons"].append([])
				ret["buttons"][lst_now + 1].append(self.make_btn(label="Назад", color="negative"))
			else:
				ret["buttons"][lst_now].append(self.make_btn(label="Назад", color="negative"))
		return json.dumps(ret, ensure_ascii=False)

	def make_kbd_day(self, group):
		tmp_dict = {
			"one_time": False,
			"buttons": [
				[
					self.make_btn(label=f"ПН_{group}", color='default'),
					self.make_btn(label=f"ВТ_{group}", color='default'),
					self.make_btn(label=f"СР_{group}", color='default'),
					self.make_btn(label=f"ЧТ_{group}", color='default'),
					self.make_btn(label=f"ПТ_{group}", color='default'),
				],
				[
					self.make_btn(label='Назад', color='negative')
				]
			]
		}
		return json.dumps(tmp_dict, ensure_ascii=False)

def result():
	messages = vk.method("messages.getConversations", {"offset":0,"count":20,"filter":"unanswered"})
	if messages["count"] >= 1:
		text = messages['items'][0]['last_message']['text']
		user_id = messages['items'][0]['last_message']['from_id']

		if text == 'Начать':
			vk.method('messages.send',{'user_id': user_id,'message': "Выберите значение", "keyboard": vk_btns.kbd_all,'random_id':random.randint(1,1000)})
		elif text == 'группы':
			vk.method('messages.send',{'user_id': user_id,'message': "Выберите группу", "keyboard": vk_btns.kbd_all,'random_id':random.randint(1,1000)})
		elif text == "Подписка на рассылку":
			vk.method('messages.send',{'user_id': user_id,'message': "Выберите группу для подписки", "keyboard": vk_btns.kbd_get_mailing,'random_id':random.randint(1,1000)})
		elif text == "Назад":
			vk.method('messages.send',{'user_id': user_id,'message': "Выберите группу","keyboard": vk_btns.kbd_all,'random_id':random.randint(1,1000)})
		elif text == "Инфо":
			vk.method('messages.send',{'user_id': user_id,'message': "Для подписки на рассылку расписания выберите вашу группу, курс. Расписание приходит ежедневно, кроме пятницы и собботы, в 18:00.\n\nВозможны несоответствия с расписанием, так как новая версия бота глорис работает в тестовом режиме! ","keyboard": vk_btns.kbd_all,'random_id':random.randint(1,1000)})

		elif text in gr_info.spec_lst:
			vk.method('messages.send',{'user_id': user_id,'message': "Выберите курс","keyboard": vk_btns.kbd_groups[text],'random_id':random.randint(1,1000)})

		elif text in gr_info.groups:
			vk.method('messages.send',{'user_id': user_id,'message': "Выберите день","keyboard": vk_btns.kbd_days[text], 'random_id':random.randint(1,1000)})

		elif text in gr_info.groups_with_days.keys():
			weekday, group = gr_info.groups_with_days[text]
			lessons_list = days_info[weekday]["groups_lesson"][group]
			vk.method('messages.send',{'user_id': user_id,'message': lessons_list,"keyboard": vk_btns.kbd_days[group],'random_id':random.randint(1,1000)})
			print(f' - Запрос на {text}, от пользователя id {str(user_id)}')

		elif text in gr_info.mailing_spec_lst:
			group = gr_info.mailing_spec_to_spec[text]
			vk.method('messages.send',{'user_id': user_id,'message': "Выберите курс","keyboard": vk_btns.kbd_mailing[group], 'random_id':random.randint(1,1000)})
		elif text in gr_info.mailing_groups_to_groups.keys():
			group = gr_info.mailing_groups_to_groups[text]
			mailing_list.append(user_id, group)
			vk.method('messages.send',{'user_id': user_id,'message': f"Вы успешно подписались на рассылку для группы {group}","keyboard": vk_btns.kbd_all,'random_id':random.randint(1,1000)})
			print(f"Пользователь id=\"{user_id}\" подписался на рассылку группы {group}")
	time.sleep(0.01)

while True:
	days_info = Days_info()
	if days_info.server_status == False:
		print("Не удается инициализировать данные о расписании. Ожидание 120 секунд до следующей попытки...")
		time.sleep(120)
		continue
	break
TOKEN = 'впишите сюда свой токен'
vk = vk_api.VkApi(token=TOKEN)
vk._auth_token()
days_info.init_ready_loop()
update_lesson_th = Update_lesson_th(days_info)
update_lesson_th.start()

gr_info = Groups_info(days_info[0]["groups"])
vk_btns = Vk_btns()
mailing_th = Mailing_th(vk)
mailing_th.start()

print("Инициализация прошла успешно и бот находится в ожидании запросов.")
while True:
	try:
		result()
	except vk_api.exceptions.ApiError as error:
		print("Error!")
